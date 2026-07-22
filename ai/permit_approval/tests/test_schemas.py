"""입출력 스키마 검증 — 명세 §5."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas.permit import (
    AreaType,
    PermitRequest,
    SpecialConditions,
    TimeWindow,
    WorkType,
    Zone,
)


def _permit(**overrides) -> PermitRequest:
    base = dict(
        permit_id="PTW-2026-000123",
        work_type=WorkType.화기작업,
        zone=Zone(block_id="B-12", area_type=AreaType.블록내부),
        time_window=TimeWindow(
            start=datetime(2026, 7, 22, 9), end=datetime(2026, 7, 22, 12)
        ),
        worker_count=3,
    )
    base.update(overrides)
    return PermitRequest(**base)


def test_명세_예시가_그대로_파싱된다():
    """명세 §5.1의 예시 JSON."""
    payload = {
        "permit_id": "PTW-2026-000123",
        "work_type": "화기작업",
        "zone": {
            "block_id": "B-12",
            "area_type": "블록내부",
            "coordinates": [12.5, 40.0],
        },
        "time_window": {
            "start": "2026-07-22T09:00:00",
            "end": "2026-07-22T12:00:00",
        },
        "worker_count": 3,
        "supervisor_present": True,
        "declared_ppe": ["안전모", "안전화", "용접보안면"],
        "work_description": "선체 외판 용접 작업",
        "special_conditions": {
            "gas_measured": False,
            "ventilation": False,
            "adjacent_flammable": True,
        },
    }
    permit = PermitRequest.model_validate(payload)
    assert permit.work_type is WorkType.화기작업
    assert permit.zone.coordinates == (12.5, 40.0)


def test_정의되지_않은_작업종류는_거부된다():
    with pytest.raises(ValidationError):
        _permit(work_type="굴착작업")


def test_종료가_시작보다_빠르면_거부된다():
    with pytest.raises(ValidationError):
        TimeWindow(start=datetime(2026, 7, 22, 12), end=datetime(2026, 7, 22, 9))


def test_시작과_종료가_같으면_거부된다():
    with pytest.raises(ValidationError):
        TimeWindow(start=datetime(2026, 7, 22, 9), end=datetime(2026, 7, 22, 9))


def test_작업인원은_1명_이상이어야_한다():
    with pytest.raises(ValidationError):
        _permit(worker_count=0)


def test_오타난_필드는_조용히_무시되지_않는다():
    """extra='forbid'. 오타 필드가 무시되면 안전 조건이 누락된 채 통과한다."""
    with pytest.raises(ValidationError):
        _permit(supervisor_presnet=True)

    with pytest.raises(ValidationError):
        SpecialConditions(gas_measure=True)


def test_시간_중첩_판정():
    a = TimeWindow(start=datetime(2026, 7, 22, 9), end=datetime(2026, 7, 22, 12))
    b = TimeWindow(start=datetime(2026, 7, 22, 11), end=datetime(2026, 7, 22, 14))
    c = TimeWindow(start=datetime(2026, 7, 22, 13), end=datetime(2026, 7, 22, 15))

    assert a.overlaps(b) and b.overlaps(a)
    assert not a.overlaps(c) and not c.overlaps(a)


def test_경계가_맞닿으면_중첩이_아니다():
    """09-12 작업과 12-15 작업은 동시에 존재하지 않는다."""
    a = TimeWindow(start=datetime(2026, 7, 22, 9), end=datetime(2026, 7, 22, 12))
    b = TimeWindow(start=datetime(2026, 7, 22, 12), end=datetime(2026, 7, 22, 15))
    assert not a.overlaps(b)
    assert not b.overlaps(a)


def test_빈_블록ID는_거부된다():
    with pytest.raises(ValidationError):
        Zone(block_id="", area_type=AreaType.도크)
