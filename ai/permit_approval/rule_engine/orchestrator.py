"""판정 종합 — 명세 §2.

이 파일이 이 모듈 전체에서 가장 중요하다. verdict를 결정하는 코드는
여기 `summarize_verdict()` 하나뿐이고, 순수 함수이며, LLM을 부르지 않는다.

4~5단계에서 Retrieval·RAG가 붙어도 순서는 바뀌지 않는다:
    verdict = summarize_verdict(violations)   ← 먼저 확정
    decision.reject_comment = llm(...)        ← 그 다음 설명만 채움
LLM은 이미 결정된 verdict를 프롬프트로 받을 뿐 되돌릴 수 없다.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from rule_engine.engine import RuleEngine
from schemas.permit import PermitDecision, PermitRequest, Severity, Verdict, Violation


def summarize_verdict(violations: Sequence[Violation]) -> Verdict:
    """위반 목록 → 판정 라벨. 명세 §2의 규칙을 그대로 코드로 고정한다.

    - hard 위반 1건이라도 있으면 → 반려
    - conditional만 있으면 → 조건부승인
    - 아무것도 없으면 → 승인제안 (그래도 최종 확정은 사람)
    """
    if any(v.severity is Severity.hard for v in violations):
        return Verdict.반려
    if violations:
        return Verdict.조건부승인
    return Verdict.승인제안


def decide(
    permit: PermitRequest,
    active_permits: Iterable[PermitRequest] = (),
    engine: RuleEngine | None = None,
) -> PermitDecision:
    """허가서 1건을 평가해 판정 결과를 만든다.

    reject_comment·recommended_actions·similar_cases는 비어 있다.
    4~5단계에서 Retrieval·LLM이 채운다. MVP는 "판정은 되지만 설명이 없는"
    상태가 정상이다 (명세 §9의 MVP 경계).
    """
    engine = engine or RuleEngine.from_config()
    violations = engine.evaluate(permit, active_permits)
    return PermitDecision(
        permit_id=permit.permit_id,
        verdict=summarize_verdict(violations),
        violations=violations,
    )
