"""RAG 생성기 본체 — 명세 §6.3·§10.

파이프라인의 순서가 이 파일의 전부다:

    verdict 확정(rule_engine) → 근거 조립(retrieval) → LLM 주입 → 설명만 생성

`generate_explanation()`이 손대는 필드는 세 개뿐이다:
`reject_comment`, `recommended_actions`, `similar_cases`. `verdict`와
`violations`는 update dict에 아예 넣지 않는다. 프롬프트 인젝션이 성공하더라도
모델이 쓴 글자가 들어갈 수 있는 곳은 설명란뿐이라는 뜻이다.

또 하나의 원칙: **LLM 실패는 판정 실패가 아니다.** 네트워크가 끊기든 JSON이
깨지든 키가 없든, 이 모듈은 예외를 밖으로 던지지 않고 설명이 빠진 원본 판정을
그대로 돌려준다. 판정은 LLM 없이 이미 유효하다.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from typing import Any, Iterable, Sequence

from config_loader import load_config
from generator.llm_client import LLMClient, LLMError, MissingCredential, get_client
from generator.prompts import SYSTEM_INSTRUCTION, build_prompt
from retrieval.searcher import SearchHit, normalize_legal_ref
from rule_engine.orchestrator import decide
from schemas.permit import PermitDecision, PermitRequest, SimilarCase

logger = logging.getLogger(__name__)

# "제241조", "제619조의2" — 공백이 섞여 들어와도 잡는다.
CITATION_RE = re.compile(r"제\s*\d+\s*조(?:\s*의\s*\d+)?")

# 문장 분리. 한국어 마침표·물음표·느낌표와 줄바꿈 기준이면 충분하다.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+|\n+")


def _canon(citation: str) -> str:
    """'제 241 조' -> '제241조'. 표기 흔들림을 흡수한다."""
    return re.sub(r"\s+", "", citation)


def allowed_citations(retrieval: dict[str, list[SearchHit]]) -> set[str]:
    """인용이 허용되는 조문 번호 집합 (명세 §10).

    검색 결과로 실제 제공한 조문만 허용한다. 본문(text) 안에 인용된 다른
    조문은 포함하지 않는다 — 제1조 본문이 제63조를 언급한다고 해서 모델이
    제63조를 근거로 들 수 있는 건 아니기 때문이다.
    """
    allowed: set[str] = set()
    for hit in retrieval.get("legal", []):
        if not hit.legal_ref:
            continue
        for match in CITATION_RE.findall(normalize_legal_ref(hit.legal_ref)):
            allowed.add(_canon(match))
    return allowed


def strip_unknown_citations(text: str, allowed: set[str]) -> tuple[str, list[str]]:
    """제공되지 않은 조문을 인용한 문장을 통째로 제거한다.

    조문 번호만 지우지 않고 문장을 지우는 이유: "제999조에 따라 감시인을
    배치해야 한다"에서 번호만 빼면 "에 따라 감시인을 배치해야 한다"는 근거
    없는 주장이 남는다. 환각의 흔적을 남기느니 문장을 버리는 게 안전하다.

    반환: (정리된 텍스트, 제거된 조문 번호 목록)
    """
    if not text:
        return text, []

    kept: list[str] = []
    removed: list[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if not sentence.strip():
            continue
        unknown = [
            _canon(c) for c in CITATION_RE.findall(sentence)
            if _canon(c) not in allowed
        ]
        if unknown:
            removed.extend(unknown)
        else:
            kept.append(sentence.strip())
    return " ".join(kept), removed


def _parse_response(raw: str) -> dict[str, Any]:
    """LLM 응답에서 JSON을 꺼낸다.

    responseMimeType=application/json을 걸어두긴 했지만, 모델이 ```json 펜스로
    감싸 보내는 경우가 있어 방어한다 (명세 §6.3 "파싱 실패 대비 방어 코드").
    """
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 앞뒤에 설명이 붙은 경우 가장 바깥 중괄호만 잘라 한 번 더 시도한다.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("응답에서 JSON을 찾지 못했다")
        data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError(f"JSON 최상위가 객체가 아니다: {type(data).__name__}")
    return data


def _coerce_actions(value: Any) -> list[str]:
    """recommended_actions를 문자열 리스트로 정규화한다."""
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _to_similar_cases(hits: Sequence[SearchHit]) -> list[SimilarCase]:
    """유사 사례는 검색 결과를 그대로 옮긴다. LLM이 만드는 값이 아니다."""
    return [
        SimilarCase(case_id=h.chunk_id, title=h.title, score=h.score)
        for h in hits
    ]


def generate_explanation(
    permit: PermitRequest,
    decision: PermitDecision,
    retrieval: dict[str, list[SearchHit]],
    client: LLMClient | None = None,
    config: dict[str, Any] | None = None,
) -> PermitDecision:
    """확정된 판정에 설명을 붙인다.

    입력 decision을 변형하지 않고 새 객체를 만들어 돌려준다. 실패 시에는
    설명 없는 원본을 그대로 돌려준다 (예외를 던지지 않는다).
    """
    config = config or load_config()
    gen_cfg = config.get("generator", {})

    # 사례는 LLM 성공 여부와 무관하게 채운다. 검색 결과 복사라 실패할 게 없다.
    updates: dict[str, Any] = {
        "similar_cases": _to_similar_cases(
            retrieval.get("cases", [])[: gen_cfg.get("context", {}).get("max_cases", 5)]
        )
    }

    try:
        client = client or get_client(config)
        raw = client.complete(
            SYSTEM_INSTRUCTION, build_prompt(permit, decision, retrieval, config)
        )
        data = _parse_response(raw)
    except (MissingCredential, LLMError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("[%s] 설명 생성 실패 — 판정만 반환한다: %s",
                       permit.permit_id, exc)
        return decision.model_copy(update=updates)

    comment = str(data.get("reject_comment", "") or "").strip()
    actions = _coerce_actions(data.get("recommended_actions"))

    if gen_cfg.get("strict_citations", True):
        allowed = allowed_citations(retrieval)
        comment, dropped = strip_unknown_citations(comment, allowed)
        clean_actions: list[str] = []
        for action in actions:
            cleaned, removed = strip_unknown_citations(action, allowed)
            dropped.extend(removed)
            if cleaned:
                clean_actions.append(cleaned)
        actions = clean_actions
        if dropped:
            logger.warning("[%s] 실재하지 않는 조문 인용 %d건 제거: %s",
                           permit.permit_id, len(dropped), sorted(set(dropped)))

    updates["reject_comment"] = comment or None
    updates["recommended_actions"] = actions

    # verdict·violations·verdict_source·human_decision_required는 update에 없다.
    # 모델이 무슨 말을 했든 판정은 그대로다.
    return decision.model_copy(update=updates)


def explain(
    permit: PermitRequest,
    active_permits: Iterable[PermitRequest] = (),
    retriever: Any | None = None,
    client: LLMClient | None = None,
    config: dict[str, Any] | None = None,
) -> PermitDecision:
    """허가서 1건의 전체 파이프라인: 판정 → 검색 → 설명.

    retriever는 인자로 받는다. PermitRetriever 생성이 임베딩 모델 2.2GB를
    로드하므로, 여러 건을 처리할 때 한 번 만들어 재사용해야 한다.
    """
    config = config or load_config()
    decision = decide(permit, active_permits)

    try:
        if retriever is None:
            from retrieval.searcher import PermitRetriever
            retriever = PermitRetriever(config)
        retrieval = retriever.retrieve(permit, decision.violations)
    except Exception as exc:  # 인덱스 부재·모델 로딩 실패 등
        logger.warning("[%s] 근거 검색 실패 — 판정만 반환한다: %s",
                       permit.permit_id, exc)
        return decision

    return generate_explanation(permit, decision, retrieval, client, config)


# --------------------------------------------------------------------------
# CLI — 스모크 실행
# --------------------------------------------------------------------------

def _print_decision(decision: PermitDecision) -> None:
    print("=" * 72)
    print(f"{decision.permit_id}  판정: {decision.verdict.value} "
          f"(주체: {decision.verdict_source}, 사람 확정 필요: "
          f"{decision.human_decision_required})")
    for v in decision.violations:
        print(f"  - [{v.rule_id}] ({v.severity.value}) {v.summary}")
        if v.legal_basis:
            print(f"      근거: {v.legal_basis}")
    print("\n[사유]")
    print(f"  {decision.reject_comment or '(생성되지 않음)'}")
    print("\n[권고 조치]")
    for action in decision.recommended_actions or ["(생성되지 않음)"]:
        print(f"  - {action}")
    print("\n[유사 사례]")
    for case in decision.similar_cases or []:
        print(f"  - {case.case_id} ({case.score:.3f}) {case.title}")
    print()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="RAG 생성기 스모크 실행 (명세 §6.3)")
    parser.add_argument(
        "--sample", type=int, default=3,
        help="합성 허가서에서 몇 건을 생성해 볼지. 판정 종류별로 고루 뽑는다.",
    )
    args = parser.parse_args()

    from data_gen.generate_permits import generate
    from retrieval.searcher import PermitRetriever

    config = load_config()
    cases, _labels = generate(100, config)

    # 판정 종류가 고루 섞이도록 verdict별로 하나씩 돌아가며 뽑는다.
    by_verdict: dict[str, list[tuple[PermitRequest, list[PermitRequest]]]] = {}
    for case in cases:
        permit = PermitRequest.model_validate(case["permit"])
        active = [PermitRequest.model_validate(a) for a in case["active_permits"]]
        verdict = decide(permit, active).verdict.value
        by_verdict.setdefault(verdict, []).append((permit, active))

    selected: list[tuple[PermitRequest, list[PermitRequest]]] = []
    while len(selected) < args.sample and any(by_verdict.values()):
        for bucket in by_verdict.values():
            if bucket and len(selected) < args.sample:
                selected.append(bucket.pop(0))

    try:
        retriever = PermitRetriever(config)
        client = get_client(config)
    except MissingCredential as exc:
        print(exc, file=sys.stderr)
        return 1

    for permit, active in selected:
        _print_decision(explain(permit, active, retriever, client, config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
