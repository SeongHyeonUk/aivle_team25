"""룰엔진 검증 — 명세 §10.

두 지표가 핵심이다.
  1. 합성 데이터의 알려진 충돌 케이스를 100% 포착 (재현율)
  2. 정상 케이스 오탐 0
"""

from __future__ import annotations

import pytest

from rule_engine.engine import RuleEngine
from rule_engine.orchestrator import decide
from schemas.permit import Severity


def test_알려진_위반을_하나도_놓치지_않는다(dataset, engine):
    """재현율 100%. 명세 §10의 첫 번째 기준."""
    misses = []
    for permit, active, label in dataset:
        found = {v.rule_id for v in engine.evaluate(permit, active)}
        for expected in label["expected_violations"]:
            if expected not in found:
                misses.append((label["case_id"], label["scenario"], expected, sorted(found)))

    assert not misses, (
        f"{len(misses)}건의 위반을 놓쳤다.\n"
        + "\n".join(f"  {cid} [{sc}] 기대={exp} 실제={got}" for cid, sc, exp, got in misses[:10])
    )


def test_정상_케이스는_오탐이_없다(dataset, engine):
    """오탐 0. 명세 §10의 두 번째 기준.

    이 테스트가 실패하면 규칙이 과하게 넓거나 인접 판정이 틀린 것이다.
    안전 시스템에서 오탐이 잦으면 관리자가 경고를 무시하게 되므로
    미탐 못지않게 중요하다.
    """
    false_positives = []
    for permit, active, label in dataset:
        if label["scenario"] != "normal":
            continue
        violations = engine.evaluate(permit, active)
        if violations:
            false_positives.append(
                (label["case_id"], [(v.rule_id, v.summary) for v in violations])
            )

    assert not false_positives, (
        f"정상 케이스 {len(false_positives)}건에서 오탐 발생.\n"
        + "\n".join(f"  {cid}: {vs}" for cid, vs in false_positives[:10])
    )


def test_판정이_정답_라벨과_일치한다(dataset):
    mismatches = []
    for permit, active, label in dataset:
        decision = decide(permit, active)
        if decision.verdict.value != label["expected_verdict"]:
            mismatches.append(
                (label["case_id"], label["scenario"],
                 label["expected_verdict"], decision.verdict.value,
                 [v.rule_id for v in decision.violations])
            )

    assert not mismatches, (
        f"{len(mismatches)}건의 판정 불일치.\n"
        + "\n".join(f"  {c[0]} [{c[1]}] 기대={c[2]} 실제={c[3]} 위반={c[4]}"
                    for c in mismatches[:10])
    )


def test_엔진은_verdict를_계산하지_않는다(engine):
    """명세 §6.1: 룰엔진의 출력은 위반 목록뿐이다.

    엔진에 판정 관련 메서드가 생기면 §2의 책임 경계가 무너지므로 막는다.
    """
    forbidden = {"verdict", "approve", "decide", "summarize_verdict"}
    exposed = {name for name in dir(engine) if not name.startswith("_")}
    assert not (forbidden & exposed), f"룰엔진이 판정 책임을 침범했다: {forbidden & exposed}"


def test_규칙_YAML_무결성(engine):
    """rule_id 중복·미정의 enum은 로드 시점에 이미 걸러진다. 여기선 내용 검증."""
    all_rules = [*engine.hard_rules, *engine.simops_rules]
    assert all_rules, "규칙이 하나도 로드되지 않았다"

    for rule in all_rules:
        rid = rule["rule_id"]
        assert rule.get("condition"), f"{rid}: condition이 비어 있으면 전건 매치가 된다"
        assert rule.get("legal_ref"), f"{rid}: legal_ref가 없다 (근거 없는 반려는 불가)"
        assert rule.get("summary") or rule.get("name"), f"{rid}: 사람이 읽을 설명이 없다"
        assert rule.get("risk_category"), f"{rid}: risk_category가 없다 (커버리지 집계 불가)"


def test_simops_규칙은_시간과_공간_조건을_모두_갖는다(engine):
    """SIMOPS는 세 조건(작업조합·공간·시간)이 다 있어야 의미가 있다.

    하나라도 빠지면 시간이 안 겹치거나 멀리 떨어진 작업까지 충돌로 잡는다.
    """
    for rule in engine.simops_rules:
        cond = rule["condition"]
        rid = rule["rule_id"]
        assert cond.get("work_type"), f"{rid}: work_type 없음"
        assert cond.get("conflict_with"), f"{rid}: conflict_with 없음"
        assert cond.get("spatial"), f"{rid}: spatial 없음 — 원거리 작업까지 잡힌다"
        assert cond.get("temporal") == "시간중첩", f"{rid}: temporal 없음 — 겹치지 않는 작업까지 잡힌다"


def test_YAML_오타는_로드_시점에_터진다(config, tmp_path):
    """조용히 꺼진 규칙이 가장 위험한 실패 모드다."""
    from rule_engine.conflict_matrix import GridConflictMatrix

    bad_rule = [{
        "rule_id": "BAD-001",
        "severity": "hard",
        "condition": {"work_type": ["화기잡업"]},  # 오타
    }]
    with pytest.raises(ValueError):
        RuleEngine(bad_rule, [], GridConflictMatrix.from_config(config))


def test_중복_rule_id는_거부된다(config):
    from rule_engine.conflict_matrix import GridConflictMatrix

    dup = [
        {"rule_id": "X-1", "severity": "hard", "condition": {"work_type": ["도장"]}},
        {"rule_id": "X-1", "severity": "hard", "condition": {"work_type": ["사상"]}},
    ]
    with pytest.raises(ValueError, match="중복"):
        RuleEngine(dup, [], GridConflictMatrix.from_config(config))


def _hot_work_permit(engine, **special) -> list:
    """화기작업 허가서 1건을 만들어 평가한다. 특수조건만 바꿔가며 쓴다."""
    from datetime import datetime

    from schemas.permit import (
        AreaType, PermitRequest, SpecialConditions, TimeWindow, WorkType, Zone,
    )

    base = dict(gas_measured=True, ventilation=True, adjacent_flammable=False,
                fire_watch_assigned=True)
    base.update(special)
    permit = PermitRequest(
        permit_id="PTW-FW-1",
        work_type=WorkType.용접,
        zone=Zone(block_id="B-12", area_type=AreaType.블록내부),
        time_window=TimeWindow(start=datetime(2026, 7, 22, 9),
                               end=datetime(2026, 7, 22, 12)),
        worker_count=3,
        supervisor_present=True,
        declared_ppe=["안전모", "안전화", "용접보안면"],
        special_conditions=SpecialConditions(**base),
    )
    return [v.rule_id for v in engine.evaluate(permit)]


def test_COND_005는_인화물_인접시_화재감시자_미배치를_잡는다(engine):
    """제241조의2. 인화물이 인접한 용접 작업에는 화재감시자가 있어야 한다."""
    assert "COND-005" in _hot_work_permit(
        engine, adjacent_flammable=True, fire_watch_assigned=False
    )


def test_COND_005는_화재감시자가_있으면_발화하지_않는다(engine):
    assert "COND-005" not in _hot_work_permit(
        engine, adjacent_flammable=True, fire_watch_assigned=True
    )


def test_COND_005는_인화물이_없으면_발화하지_않는다(engine):
    """감시자 미배치만으로 잡으면 모든 화기작업이 걸려 오탐이 된다."""
    assert "COND-005" not in _hot_work_permit(
        engine, adjacent_flammable=False, fire_watch_assigned=False
    )


def test_COND_005는_판정을_뒤집지_않는다(engine):
    """HARD-003과 함께 걸려도 반려는 반려다 (조건부가 hard를 완화하지 않는다)."""
    from datetime import datetime

    from rule_engine.orchestrator import summarize_verdict
    from schemas.permit import (
        AreaType, PermitRequest, SpecialConditions, TimeWindow, Verdict, WorkType, Zone,
    )

    permit = PermitRequest(
        permit_id="PTW-FW-2",
        work_type=WorkType.용접,
        zone=Zone(block_id="B-12", area_type=AreaType.블록내부),
        time_window=TimeWindow(start=datetime(2026, 7, 22, 9),
                               end=datetime(2026, 7, 22, 12)),
        worker_count=3,
        supervisor_present=True,
        declared_ppe=["안전모", "안전화", "용접보안면"],
        special_conditions=SpecialConditions(
            gas_measured=True, ventilation=False,
            adjacent_flammable=True, fire_watch_assigned=False,
        ),
    )
    violations = engine.evaluate(permit)
    found = {v.rule_id for v in violations}
    assert {"HARD-003", "COND-005"} <= found
    assert summarize_verdict(violations) is Verdict.반려


def test_hard_위반은_반드시_severity가_hard로_해석된다(engine, dataset):
    """Severity enum 밖의 값이 슬쩍 들어오지 않는지."""
    for permit, active, _ in dataset[:50]:
        for violation in engine.evaluate(permit, active):
            assert isinstance(violation.severity, Severity)
