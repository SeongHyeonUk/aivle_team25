"""합성 데이터 생성기 검증 — 명세 §8."""

from __future__ import annotations

import pytest

from data_gen.generate_permits import generate
from schemas.permit import RiskCategory


def test_요청한_건수_이상_생성된다(config):
    cases, labels = generate(100, config)
    # 커버리지 보강분이 뒤에 붙을 수 있으므로 정확히 같지는 않다.
    assert len(cases) >= 100
    assert len(cases) == len(labels)


def test_같은_seed는_같은_결과를_낸다(config):
    """명세 §8: 재현성을 위해 seed 고정."""
    first_cases, first_labels = generate(100, config)
    second_cases, second_labels = generate(100, config)
    assert first_cases == second_cases
    assert first_labels == second_labels


def test_다른_seed는_다른_결과를_낸다(config):
    """seed가 실제로 쓰이는지 확인 (전역 random 오용 탐지)."""
    other = {**config, "data_gen": {**config["data_gen"], "seed": 999}}
    assert generate(100, config)[0] != generate(100, other)[0]


def test_시나리오_비율이_설정을_따른다(config):
    _, labels = generate(1000, config)
    counts: dict[str, int] = {}
    for label in labels:
        counts[label["scenario"]] = counts.get(label["scenario"], 0) + 1

    for name, ratio in config["data_gen"]["scenario_mix"].items():
        actual = counts.get(name, 0) / len(labels)
        assert abs(actual - ratio) < 0.02, f"{name}: 기대 {ratio:.0%}, 실제 {actual:.1%}"


def test_네_가지_위험_카테고리가_모두_발화된다(config):
    """명세 §8: 코드로 커버리지를 보장할 것."""
    _, labels = generate(60, config)
    covered = {c for label in labels for c in label["risk_categories"]}
    required = set(config["data_gen"]["required_risk_categories"])
    assert required.issubset(covered), f"누락된 카테고리: {required - covered}"


def test_아주_작은_표본에서도_커버리지가_보장된다(config):
    """비율만 믿으면 소표본에서 카테고리가 빈다. 강제 주입이 작동하는지."""
    _, labels = generate(5, config)
    covered = {c for label in labels for c in label["risk_categories"]}
    assert {c.value for c in RiskCategory}.issubset(covered)


def test_커버리지_보강_빌더는_해당_카테고리를_반드시_발화시킨다(config):
    """랜덤 선택지에 다른 카테고리가 섞이면 주입하고도 미달이 난다.

    실제로 혼재 폴백이 build_simops_conflict를 쓰던 시절 이 문제로 소표본에서
    커버리지 보장이 깨졌다. 빌더를 바꿀 때 재발하지 않도록 고정한다.
    """
    import random

    from data_gen.generate_permits import CATEGORY_FALLBACK, YardLayout, _rule_index

    index = _rule_index(config)
    yard = config["data_gen"]["yard"]
    layout = YardLayout(yard["block_prefixes"], yard["grid_rows"], yard["grid_cols"])

    for category, (_, builder) in CATEGORY_FALLBACK.items():
        for seed in range(30):  # 랜덤 분기를 충분히 훑는다
            _, _, expected = builder(random.Random(seed), layout, f"T-{seed}")
            produced = {index[r]["risk_category"] for r in expected}
            assert category in produced, (
                f"{builder.__name__}(seed={seed})가 {category.value}를 발화시키지 못했다: {expected}"
            )


def test_비율_합이_1이_아니면_거부된다(config):
    broken = {
        **config,
        "data_gen": {**config["data_gen"], "scenario_mix": {"normal": 0.5, "confined_space": 0.2}},
    }
    with pytest.raises(ValueError, match="1.0"):
        generate(100, broken)


def test_정상_케이스에는_기대_위반이_없다(config):
    _, labels = generate(200, config)
    for label in labels:
        if label["scenario"] == "normal":
            assert label["expected_violations"] == []
            assert label["expected_verdict"] == "승인제안"


def test_case_id가_고유하다(config):
    cases, _ = generate(300, config)
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_허가서_id도_고유하다(config):
    """SIMOPS 평가에서 자기 자신을 상대로 오인하지 않으려면 필요하다."""
    cases, _ = generate(300, config)
    permit_ids = [c["permit"]["permit_id"] for c in cases]
    assert len(permit_ids) == len(set(permit_ids))
