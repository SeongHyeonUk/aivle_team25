"""공용 픽스처.

합성 데이터는 파일이 아니라 generate()를 직접 호출해 메모리에서 만든다.
테스트가 `python -m data_gen.generate_permits` 선행 실행에 의존하지 않게 하려는
것이다. seed가 고정돼 있으므로 파일로 만든 것과 동일한 데이터가 나온다.
"""

from __future__ import annotations

import pytest

from config_loader import load_config
from data_gen.generate_permits import generate
from rule_engine.engine import RuleEngine
from schemas.permit import PermitRequest

CASE_COUNT = 300


@pytest.fixture(scope="session")
def config() -> dict:
    return load_config()


@pytest.fixture(scope="session")
def engine(config) -> RuleEngine:
    return RuleEngine.from_config(config)


@pytest.fixture(scope="session")
def dataset(config) -> list[tuple[PermitRequest, list[PermitRequest], dict]]:
    """(신규 허가서, 진행 중 허가서 목록, 정답 라벨) 튜플 목록."""
    cases, labels = generate(CASE_COUNT, config)
    assert len(cases) == len(labels)
    return [
        (
            PermitRequest.model_validate(case["permit"]),
            [PermitRequest.model_validate(a) for a in case["active_permits"]],
            label,
        )
        for case, label in zip(cases, labels)
    ]
