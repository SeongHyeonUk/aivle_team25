"""손으로 만든 허가서를 실제 파이프라인에 태워보는 실행기.

합성 데이터가 아니라 `samples/permits/*.json`(P-94 양식 기반)을 읽는다.
직접 편집한 파일을 `--file`로 넣어도 된다.

    python -m tools.try_permit --list
    python -m tools.try_permit hot-work-tank
    python -m tools.try_permit --all --no-llm
    python -m tools.try_permit --file 내허가서.json

`--no-llm`은 룰엔진 + 검색까지만 돌린다. LLM 무료 티어 쿼터를 아끼거나
판정 로직만 확인할 때 쓴다. 판정 자체는 LLM과 무관하므로 결과가 같다.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from config_loader import ROOT
from schemas.permit import PermitDecision, PermitRequest

SAMPLE_DIR = ROOT / "samples" / "permits"

VERDICT_MARK = {"승인제안": "○", "조건부승인": "△", "반려": "✕"}


def _load_case(path: Path) -> tuple[str, PermitRequest, list[PermitRequest]]:
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name}: JSON 형식 오류 — {exc}")

    if "permit" not in raw:
        raise SystemExit(
            f"{path.name}: 최상위에 'permit' 키가 없다.\n"
            "형식: {\"note\": \"...\", \"permit\": {...}, \"active_permits\": [...]}"
        )

    from pydantic import ValidationError
    try:
        permit = PermitRequest.model_validate(raw["permit"])
        active = [PermitRequest.model_validate(a) for a in raw.get("active_permits", [])]
    except ValidationError as exc:
        raise SystemExit(f"{path.name}: 스키마 검증 실패\n{exc}")

    return raw.get("note", ""), permit, active


def _print_permit(permit: PermitRequest, active: list[PermitRequest]) -> None:
    sc = permit.special_conditions
    tw = permit.time_window
    print(f"  작업        {permit.work_type.value} / {permit.zone.block_id} "
          f"({permit.zone.area_type.value}) / {permit.worker_count}명")
    print(f"  시간        {tw.start:%m-%d %H:%M} ~ {tw.end:%H:%M}")
    print(f"  안전조치    가스측정 {'O' if sc.gas_measured else 'X'} · "
          f"환기 {'O' if sc.ventilation else 'X'} · "
          f"인화물인접 {'O' if sc.adjacent_flammable else 'X'} · "
          f"화재감시자 {'O' if sc.fire_watch_assigned else 'X'} · "
          f"감독자 {'O' if permit.supervisor_present else 'X'}")
    print(f"  보호구      {', '.join(permit.declared_ppe) or '(없음)'}")
    if active:
        print("  진행 중     " + " / ".join(
            f"{a.permit_id} {a.work_type.value}@{a.zone.block_id} "
            f"{a.time_window.start:%H:%M}-{a.time_window.end:%H:%M}" for a in active
        ))


def _print_decision(decision: PermitDecision, with_llm: bool) -> None:
    mark = VERDICT_MARK.get(decision.verdict.value, "?")
    print()
    print(f"  ▶ 판정      {mark} {decision.verdict.value}   "
          f"(판정 주체: {decision.verdict_source} / "
          f"사람 확정 필요: {decision.human_decision_required})")

    if decision.violations:
        print("  ▶ 위반")
        for v in decision.violations:
            tag = "hard" if v.severity.value == "hard" else "cond"
            print(f"      [{tag}] {v.rule_id}  {v.summary}")
            if v.legal_basis:
                print(f"             근거: {v.legal_basis}")
            if v.conflicting_permit:
                print(f"             충돌: {v.conflicting_permit}")
    else:
        print("  ▶ 위반      없음")

    if with_llm:
        print()
        print("  ▶ 사유")
        print(f"      {decision.reject_comment or '(생성되지 않음 — LLM 호출 실패)'}")
        if decision.recommended_actions:
            print("  ▶ 권고 조치")
            for a in decision.recommended_actions:
                print(f"      - {a}")

    if decision.similar_cases:
        print("  ▶ 유사 사례")
        for c in decision.similar_cases[:3]:
            print(f"      ({c.score:.3f}) {c.title}")


def _run(path: Path, retriever, client, config, with_llm: bool) -> str:
    note, permit, active = _load_case(path)

    print("=" * 78)
    print(f"{path.stem}   [{permit.permit_id}]")
    if note:
        print(f"  의도        {note}")
    print("-" * 78)
    _print_permit(permit, active)

    if with_llm or retriever is not None:
        from generator.rag import explain
        decision = explain(permit, active, retriever, client, config)
    else:
        from rule_engine.orchestrator import decide
        decision = decide(permit, active)

    _print_decision(decision, with_llm)
    print()
    return decision.verdict.value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="P-94 양식 기반 샘플 허가서를 실제 파이프라인에 태워본다"
    )
    parser.add_argument("name", nargs="?", help="샘플 이름 (일부만 적어도 된다)")
    parser.add_argument("--list", action="store_true", help="샘플 목록만 출력")
    parser.add_argument("--all", action="store_true", help="모든 샘플 실행")
    parser.add_argument("--file", type=Path, help="직접 만든 JSON 파일 실행")
    parser.add_argument("--no-llm", action="store_true",
                        help="LLM 호출 없이 룰엔진 판정만 (쿼터 절약)")
    parser.add_argument("--no-retrieval", action="store_true",
                        help="검색까지 생략 (임베딩 모델 로딩 없이 즉시 실행)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="  ! %(message)s")

    samples = sorted(SAMPLE_DIR.glob("*.json"))
    if not samples and not args.file:
        print(f"샘플이 없다: {SAMPLE_DIR}", file=sys.stderr)
        return 1

    if args.list:
        print(f"샘플 {len(samples)}건  ({SAMPLE_DIR})\n")
        for p in samples:
            note, permit, active = _load_case(p)
            print(f"  {p.stem:34s} {permit.work_type.value:8s} "
                  f"{permit.zone.block_id:6s} 진행중 {len(active)}건")
            if note:
                print(f"  {'':34s} {note[:80]}")
        return 0

    # 실행 대상 선정
    if args.file:
        targets = [args.file]
        if not args.file.exists():
            print(f"파일이 없다: {args.file}", file=sys.stderr)
            return 1
    elif args.all:
        targets = samples
    elif args.name:
        targets = [p for p in samples if args.name.lower() in p.stem.lower()]
        if not targets:
            print(f"'{args.name}'과 일치하는 샘플이 없다. --list로 확인할 것.",
                  file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    from config_loader import load_config
    config = load_config()

    retriever = None
    client = None
    with_llm = not args.no_llm

    if not args.no_retrieval:
        try:
            from retrieval.searcher import PermitRetriever
            print("검색 인덱스 로딩 중... (최초 1회, 수십 초)", file=sys.stderr)
            retriever = PermitRetriever(config)
        except Exception as exc:
            print(f"검색을 쓸 수 없다 — 판정만 진행한다: {exc}", file=sys.stderr)
            with_llm = False
    else:
        with_llm = False

    if with_llm:
        try:
            from generator.llm_client import MissingCredential, get_client
            client = get_client(config)
        except MissingCredential as exc:
            print(exc, file=sys.stderr)
            with_llm = False

    print()
    results = [_run(p, retriever, client, config, with_llm) for p in targets]

    if len(results) > 1:
        print("=" * 78)
        summary = {v: results.count(v) for v in sorted(set(results))}
        print("요약  " + " / ".join(
            f"{VERDICT_MARK.get(k, '?')} {k} {n}건" for k, n in summary.items()))
        print("      최종 승인은 사람이 한다. 시스템은 어떤 허가서도 자동 승인하지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
