"""합성 작업허가서 생성 — 명세 §8.

실제 조선소 허가서는 기밀이라 사용할 수 없다(명세 §11). 대신 KOSHA P-94 /
OSHA 1915 공개 표준 구조를 따르는 데이터를 생성한다.

=== 라벨 누수 경고 (명세 §8) ===
여기서 만드는 labels.jsonl은 **룰엔진 테스트용 정답지**다. XGBoost 등 다른
모듈이 이 값을 위험도 학습 라벨로 그대로 복사하면 모델은 룰엔진을 복제할 뿐
아무것도 학습하지 못한다. 학습 라벨은 룰 점수를 확률로 삼아 사고 발생을
확률적으로 샘플링하고 룰에 없는 상호작용 변수를 심어 별도로 만들어야 한다.
TODO(팀확인): 실제 라벨 생성 방식은 XGBoost 모듈과 인터페이스 협의 필요.

=== 출력 형식 ===
permits.jsonl : 한 줄 = 평가 케이스 1건
    {"case_id", "permit": {...}, "active_permits": [{...}, ...]}
    명세 §1의 입력 정의("신규 허가서 1건 + 진행 중 허가서 목록")를 그대로 옮겼다.
labels.jsonl  : 한 줄 = 그 케이스의 정답
    {"case_id", "permit_id", "scenario", "expected_violations", "expected_verdict",
     "risk_categories"}

expected_violations는 생성기가 **의도적으로 심은** 규칙 ID다. 룰엔진이 이보다
더 많이 잡는 것은 허용되지만(부수 위반), 하나라도 놓치면 재현율 실패다.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from config_loader import load_config, resolve
from rule_engine.engine import RuleEngine
from schemas.permit import (
    AreaType,
    PermitRequest,
    RiskCategory,
    Severity,
    SpecialConditions,
    TimeWindow,
    Verdict,
    WorkType,
    Zone,
)

BASE_DATE = datetime(2026, 7, 22)

# 작업 종류별 필수 PPE. COND-001(용접보안면 누락)과 맞물린다.
REQUIRED_PPE: dict[WorkType, list[str]] = {
    WorkType.화기작업: ["안전모", "안전화", "용접보안면", "방염복"],
    WorkType.용접: ["안전모", "안전화", "용접보안면", "방염복"],
    WorkType.도장: ["안전모", "안전화", "방독마스크", "보호의"],
    WorkType.사상: ["안전모", "안전화", "방진마스크", "보안경"],
    WorkType.양중: ["안전모", "안전화", "안전대"],
    WorkType.밀폐공간작업: ["안전모", "안전화", "송기마스크", "안전대"],
    WorkType.취부: ["안전모", "안전화", "보안경"],
    WorkType.일반: ["안전모", "안전화"],
}

DESCRIPTION_TEMPLATES: dict[WorkType, str] = {
    WorkType.화기작업: "{block} {area} 화기작업 - 배관 절단 및 개선 작업",
    WorkType.용접: "{block} {area} 선체 외판 용접 작업",
    WorkType.도장: "{block} {area} 방청 프라이머 도장 작업",
    WorkType.사상: "{block} {area} 용접부 그라인딩 사상 작업",
    WorkType.양중: "{block} {area} 블록 인양 및 반전 작업",
    WorkType.밀폐공간작업: "{block} {area} 내부 청소 및 검사 작업",
    WorkType.취부: "{block} {area} 부재 취부 및 가용접 작업",
    WorkType.일반: "{block} {area} 자재 정리 및 준비 작업",
}


class YardLayout:
    """블록 ID 생성·인접 블록 탐색. conflict_matrix.py의 그리드 가정과 맞춘다."""

    def __init__(self, prefixes: list[str], rows: int, cols: int) -> None:
        self.prefixes = prefixes
        self.rows = rows
        self.cols = cols

    def block(self, prefix: str, index: int) -> str:
        return f"{prefix}-{index:02d}"

    def random_block(self, rng: random.Random) -> tuple[str, int]:
        return rng.choice(self.prefixes), rng.randint(1, self.rows * self.cols)

    def adjacent_index(self, index: int, rng: random.Random) -> int:
        """같은 접두사 내에서 체비쇼프 거리 1인 다른 블록 번호를 고른다."""
        row, col = (index - 1) // self.cols, (index - 1) % self.cols
        candidates = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    candidates.append(r * self.cols + c + 1)
        return rng.choice(candidates)

    def other_prefix(self, prefix: str, rng: random.Random) -> str:
        others = [p for p in self.prefixes if p != prefix]
        return rng.choice(others) if others else prefix


def _window(rng: random.Random, start_hour: int | None = None) -> TimeWindow:
    hour = start_hour if start_hour is not None else rng.choice([8, 9, 10, 13])
    duration = rng.choice([3, 4, 5])
    start = BASE_DATE + timedelta(hours=hour)
    return TimeWindow(start=start, end=start + timedelta(hours=duration))


def _disjoint_window(rng: random.Random, other: TimeWindow) -> TimeWindow:
    """other와 절대 겹치지 않는 창. 정상 케이스의 배경 허가서용."""
    start = other.end + timedelta(hours=rng.randint(1, 3))
    return TimeWindow(start=start, end=start + timedelta(hours=rng.choice([2, 3])))


def _safe_permit(
    rng: random.Random,
    layout: YardLayout,
    permit_id: str,
    work_type: WorkType,
    block: str,
    window: TimeWindow,
    area_type: AreaType | None = None,
) -> PermitRequest:
    """어떤 단일 규칙에도 걸리지 않는 허가서.

    시나리오 빌더는 이 함수로 안전한 기본값을 만든 뒤, 의도한 위반 차원
    **하나만** 어긋뜨린다. 그래야 labels의 expected_verdict가 부수 위반 때문에
    뒤집히지 않는다.
    """
    if area_type is None:
        area_type = (
            AreaType.탱크 if work_type is WorkType.밀폐공간작업
            else rng.choice([AreaType.블록내부, AreaType.도크, AreaType.개방구역])
        )
    return PermitRequest(
        permit_id=permit_id,
        work_type=work_type,
        zone=Zone(
            block_id=block,
            area_type=area_type,
            coordinates=(round(rng.uniform(0, 200), 1), round(rng.uniform(0, 120), 1)),
        ),
        time_window=window,
        worker_count=rng.randint(2, 8),          # COND-004(10인 이상) 회피
        supervisor_present=True,                  # HARD-002 / COND-003 회피
        declared_ppe=list(REQUIRED_PPE[work_type]),  # COND-001 회피
        work_description=DESCRIPTION_TEMPLATES[work_type].format(
            block=block, area=area_type.value
        ),
        special_conditions=SpecialConditions(
            gas_measured=True,        # HARD-001 회피
            ventilation=True,         # HARD-004 / COND-002 회피
            adjacent_flammable=False,  # HARD-003 회피
            fire_watch_assigned=True,  # COND-005 회피
        ),
    )


# --------------------------------------------------------------------------
# 시나리오 빌더
#
# 각 빌더는 (permit, active_permits, expected_violations)를 반환한다.
# --------------------------------------------------------------------------

Case = tuple[PermitRequest, list[PermitRequest], list[str]]
Builder = Callable[[random.Random, YardLayout, str], Case]


def build_normal(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """위반 없음. 배경 허가서는 다른 구역(원거리)에 두고 시간도 어긋낸다."""
    work_type = rng.choice(list(WorkType))
    prefix, index = layout.random_block(rng)
    window = _window(rng)
    permit = _safe_permit(rng, layout, f"{cid}-N", work_type, layout.block(prefix, index), window)

    active = []
    for i in range(rng.randint(0, 2)):
        # 다른 접두사 = 원거리(conflict_matrix.prefix_isolates) + 시간도 분리.
        # 두 겹으로 막아 오탐 가능성을 없앤다.
        other_prefix = layout.other_prefix(prefix, rng)
        _, other_index = layout.random_block(rng)
        active.append(
            _safe_permit(
                rng, layout, f"{cid}-A{i}", rng.choice(list(WorkType)),
                layout.block(other_prefix, other_index), _disjoint_window(rng, window),
            )
        )
    return permit, active, []


def _simops_case(
    rng: random.Random,
    layout: YardLayout,
    cid: str,
    new_type: WorkType,
    active_type: WorkType,
    rule_id: str,
    spatial: str,
) -> Case:
    prefix, index = layout.random_block(rng)
    if spatial == "동일구역":
        active_block = layout.block(prefix, index)
    else:
        active_block = layout.block(prefix, layout.adjacent_index(index, rng))

    window = _window(rng, start_hour=9)
    # 확실히 겹치는 창 (09:00 시작 작업 위에 10:00~13:00을 얹는다)
    overlap = TimeWindow(
        start=window.start + timedelta(hours=1),
        end=window.start + timedelta(hours=4),
    )
    permit = _safe_permit(rng, layout, f"{cid}-N", new_type, layout.block(prefix, index), window)
    active = [_safe_permit(rng, layout, f"{cid}-A0", active_type, active_block, overlap)]
    return permit, active, [rule_id]


SIMOPS_COMBOS = [
    (WorkType.화기작업, WorkType.밀폐공간작업, "SIMOPS-001", "동일구역"),
    (WorkType.양중, WorkType.취부, "SIMOPS-002", "동일구역"),
    (WorkType.도장, WorkType.사상, "SIMOPS-003", "동일구역"),
    (WorkType.용접, WorkType.도장, "SIMOPS-004", "인접구역"),
    (WorkType.밀폐공간작업, WorkType.도장, "SIMOPS-005", "인접구역"),
]

# 혼재 카테고리를 확실히 발화시키는 조합만 추린 것. 커버리지 강제 주입용이다.
# (SIMOPS-002는 인적, 004는 화재폭발, 005는 질식중독이라 혼재를 보장하지 못한다.)
SIMOPS_MIXED_COMBOS = [c for c in SIMOPS_COMBOS if c[2] in {"SIMOPS-001", "SIMOPS-003"}]


def build_simops_conflict(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """혼재작업 충돌. 규칙별 조합을 균등하게 돌린다."""
    return _simops_case(rng, layout, cid, *rng.choice(SIMOPS_COMBOS))


def build_simops_mixed(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """혼재 카테고리 전용. 커버리지 보강 시에만 쓰인다."""
    return _simops_case(rng, layout, cid, *rng.choice(SIMOPS_MIXED_COMBOS))


def build_hot_work_flammable(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """화기-인화물.

    HARD-003(인화물+환기없음) / HARD-004(탱크+환기없음) / COND-005(감시자 미배치).

    COND-005은 환기를 정상으로 두어 hard 위반과 섞이지 않게 한다. 그래야
    조건부승인 라벨이 반려에 먹히지 않는다.
    """
    work_type = rng.choice([WorkType.화기작업, WorkType.용접])
    prefix, index = layout.random_block(rng)
    block = layout.block(prefix, index)
    window = _window(rng)

    variant = rng.choice(["adjacent_flammable", "tank", "no_fire_watch"])
    if variant == "adjacent_flammable":
        permit = _safe_permit(rng, layout, f"{cid}-N", work_type, block, window,
                              area_type=AreaType.블록내부)
        permit = permit.model_copy(update={
            "special_conditions": SpecialConditions(
                gas_measured=True, ventilation=False, adjacent_flammable=True,
                fire_watch_assigned=True,
            )
        })
        expected = ["HARD-003"]
    elif variant == "tank":
        permit = _safe_permit(rng, layout, f"{cid}-N", work_type, block, window,
                              area_type=AreaType.탱크)
        permit = permit.model_copy(update={
            "special_conditions": SpecialConditions(
                gas_measured=True, ventilation=False, adjacent_flammable=False,
                fire_watch_assigned=True,
            )
        })
        expected = ["HARD-004"]
    else:
        permit = _safe_permit(rng, layout, f"{cid}-N", work_type, block, window,
                              area_type=AreaType.블록내부)
        permit = permit.model_copy(update={
            "special_conditions": SpecialConditions(
                gas_measured=True, ventilation=True, adjacent_flammable=True,
                fire_watch_assigned=False,
            )
        })
        expected = ["COND-005"]
    return permit, [], expected


def build_confined_space(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """밀폐공간. 가스 미측정(hard) / 감시인 부재(hard) / 환기 없음(conditional)."""
    prefix, index = layout.random_block(rng)
    block = layout.block(prefix, index)
    permit = _safe_permit(rng, layout, f"{cid}-N", WorkType.밀폐공간작업, block,
                          _window(rng), area_type=AreaType.탱크)

    variant = rng.choice(["no_gas", "no_supervisor", "no_ventilation"])
    if variant == "no_gas":
        permit = permit.model_copy(update={
            "special_conditions": SpecialConditions(
                gas_measured=False, ventilation=True, adjacent_flammable=False
            )
        })
        expected = ["HARD-001"]
    elif variant == "no_supervisor":
        permit = permit.model_copy(update={"supervisor_present": False})
        expected = ["HARD-002"]
    else:
        permit = permit.model_copy(update={
            "special_conditions": SpecialConditions(
                gas_measured=True, ventilation=False, adjacent_flammable=False
            )
        })
        expected = ["COND-002"]
    return permit, [], expected


def build_ppe_missing(rng: random.Random, layout: YardLayout, cid: str) -> Case:
    """COND-001. 인적 카테고리 커버리지 보강용."""
    work_type = rng.choice([WorkType.화기작업, WorkType.용접])
    prefix, index = layout.random_block(rng)
    permit = _safe_permit(rng, layout, f"{cid}-N", work_type,
                          layout.block(prefix, index), _window(rng),
                          area_type=AreaType.블록내부)
    permit = permit.model_copy(update={
        "declared_ppe": [p for p in REQUIRED_PPE[work_type] if p != "용접보안면"]
    })
    return permit, [], ["COND-001"]


BUILDERS: dict[str, Builder] = {
    "normal": build_normal,
    "simops_conflict": build_simops_conflict,
    "simops_mixed": build_simops_mixed,
    "hot_work_flammable": build_hot_work_flammable,
    "confined_space": build_confined_space,
    "ppe_missing": build_ppe_missing,
}

# 카테고리 커버리지가 미달일 때 강제로 주입할 빌더.
# 각 빌더는 해당 카테고리를 **반드시** 발화시켜야 한다. 랜덤 선택지 안에
# 다른 카테고리가 섞인 빌더를 쓰면 주입하고도 여전히 미달일 수 있다.
CATEGORY_FALLBACK: dict[RiskCategory, tuple[str, Builder]] = {
    RiskCategory.인적: ("ppe_missing", build_ppe_missing),          # COND-001 고정
    RiskCategory.화재폭발: ("hot_work_flammable", build_hot_work_flammable),  # HARD-003/004
    RiskCategory.질식중독: ("confined_space", build_confined_space),  # HARD-001/002, COND-002
    RiskCategory.혼재: ("simops_mixed", build_simops_mixed),        # SIMOPS-001/003
}


def _rule_index(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """rule_id → {severity, risk_category}.

    YAML을 단일 진실 공급원으로 삼는다. 여기에 표를 따로 두면 규칙을 고칠 때
    한쪽만 바뀌어 정답지가 조용히 틀어진다.
    """
    engine = RuleEngine.from_config(config)
    return {
        rule["rule_id"]: {
            "severity": Severity(rule.get("severity", "conditional")),
            "risk_category": RiskCategory(rule["risk_category"]) if rule.get("risk_category") else None,
        }
        for rule in [*engine.hard_rules, *engine.simops_rules]
    }


def _expected_verdict(expected: list[str], index: dict[str, dict[str, Any]]) -> Verdict:
    """의도한 위반만으로 계산한 판정. orchestrator와 같은 규칙을 따른다."""
    severities = [index[r]["severity"] for r in expected]
    if any(s is Severity.hard for s in severities):
        return Verdict.반려
    if severities:
        return Verdict.조건부승인
    return Verdict.승인제안


def _pick_scenarios(rng: random.Random, count: int, mix: dict[str, float]) -> list[str]:
    """비율대로 시나리오를 배분한다. 반올림 잔여는 normal로 채운다."""
    total = sum(mix.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"data_gen.scenario_mix의 합이 1.0이 아니다: {total}")

    scenarios: list[str] = []
    for name, ratio in mix.items():
        scenarios.extend([name] * int(count * ratio))
    while len(scenarios) < count:
        scenarios.append("normal")
    rng.shuffle(scenarios)
    return scenarios[:count]


def generate(count: int, config: dict[str, Any] | None = None) -> tuple[list[dict], list[dict]]:
    config = config or load_config()
    dg = config["data_gen"]
    rng = random.Random(dg["seed"])  # 전역 random 사용 금지 — 재현성이 깨진다
    yard = dg["yard"]
    layout = YardLayout(yard["block_prefixes"], yard["grid_rows"], yard["grid_cols"])

    index = _rule_index(config)
    scenarios = _pick_scenarios(rng, count, dg["scenario_mix"])
    cases: list[dict] = []
    labels: list[dict] = []

    def emit(scenario: str, seq: int) -> None:
        case_id = f"CASE-{seq:05d}"
        permit, active, expected = BUILDERS[scenario](rng, layout, case_id)
        cases.append({
            "case_id": case_id,
            "permit": permit.model_dump(mode="json"),
            "active_permits": [a.model_dump(mode="json") for a in active],
        })
        labels.append({
            "case_id": case_id,
            "permit_id": permit.permit_id,
            "scenario": scenario,
            "expected_violations": expected,
            "expected_verdict": _expected_verdict(expected, index).value,
            "risk_categories": sorted(
                {index[r]["risk_category"].value for r in expected if index[r]["risk_category"]}
            ),
        })

    for seq, scenario in enumerate(scenarios):
        emit(scenario, seq)

    # 명세 §8: 4개 위험 카테고리가 모두 발화되는 커버리지를 코드로 보장한다.
    required = {RiskCategory(c) for c in dg["required_risk_categories"]}
    covered = {RiskCategory(c) for label in labels for c in label["risk_categories"]}
    for missing in sorted(required - covered, key=lambda c: c.value):
        scenario, _ = CATEGORY_FALLBACK[missing]
        emit(scenario, len(labels))

    covered = {RiskCategory(c) for label in labels for c in label["risk_categories"]}
    if not required.issubset(covered):
        raise RuntimeError(
            f"위험 카테고리 커버리지 확보 실패. 누락: {sorted(c.value for c in required - covered)}"
        )
    return cases, labels


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description="합성 작업허가서 생성 (명세 §8)")
    parser.add_argument("--count", type=int, default=config["data_gen"]["default_count"])
    parser.add_argument("--out", type=str, default=None, help="출력 디렉터리 (기본: config)")
    args = parser.parse_args()

    cases, labels = generate(args.count, config)
    out_dir = Path(args.out) if args.out else resolve(config["paths"]["synthetic_dir"])
    _write_jsonl(out_dir / "permits.jsonl", cases)
    _write_jsonl(out_dir / "labels.jsonl", labels)

    print(f"생성 완료: {len(cases)}건 -> {out_dir}")
    print("\n시나리오 분포")
    counts: dict[str, int] = {}
    for label in labels:
        counts[label["scenario"]] = counts.get(label["scenario"], 0) + 1
    for name in sorted(counts):
        print(f"  {name:22s} {counts[name]:5d} ({counts[name] / len(labels):6.1%})")

    print("\n위험 카테고리 커버리지")
    cat_counts: dict[str, int] = {}
    for label in labels:
        for cat in label["risk_categories"]:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat in config["data_gen"]["required_risk_categories"]:
        n = cat_counts.get(cat, 0)
        print(f"  {cat:10s} {n:5d}건  {'OK' if n else '누락'}")


if __name__ == "__main__":
    main()
