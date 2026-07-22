"""블록 인접 판정 검증 — 명세 §6.1.

grid_cols=6 기준 배치:
    B-01 B-02 B-03 B-04 B-05 B-06
    B-07 B-08 B-09 B-10 B-11 B-12
    B-13 B-14 B-15 B-16 B-17 B-18
"""

from __future__ import annotations

import pytest

from rule_engine.conflict_matrix import GridConflictMatrix
from schemas.permit import SpatialRelation


@pytest.fixture
def matrix() -> GridConflictMatrix:
    return GridConflictMatrix(grid_cols=6, adjacency_distance=1, prefix_isolates=True)


def test_같은_블록은_동일구역(matrix):
    assert matrix.relation("B-12", "B-12") is SpatialRelation.동일구역


def test_대소문자_차이는_같은_블록으로_본다(matrix):
    assert matrix.relation("b-12", "B-12") is SpatialRelation.동일구역


def test_좌우_이웃은_인접구역(matrix):
    assert matrix.relation("B-11", "B-12") is SpatialRelation.인접구역


def test_상하_이웃은_인접구역(matrix):
    # B-06(0행 5열) 바로 아래는 B-12(1행 5열)
    assert matrix.relation("B-06", "B-12") is SpatialRelation.인접구역


def test_대각_이웃은_인접구역(matrix):
    # B-05(0행 4열) 대각 아래는 B-12(1행 5열)
    assert matrix.relation("B-05", "B-12") is SpatialRelation.인접구역


def test_행이_바뀌는_경계에서_줄바꿈이_반영된다(matrix):
    """B-06은 0행 끝, B-07은 1행 시작. 번호는 붙어 있지만 열이 5→0이라 멀다."""
    assert matrix.relation("B-06", "B-07") is SpatialRelation.원거리


def test_먼_블록은_원거리(matrix):
    assert matrix.relation("B-01", "B-12") is SpatialRelation.원거리


def test_다른_구역은_원거리(matrix):
    assert matrix.relation("A-12", "B-12") is SpatialRelation.원거리


def test_파싱할_수_없는_식별자는_원거리(matrix):
    """근거 없이 인접을 주장하지 않는다 (오탐 0 목표 우선)."""
    assert matrix.relation("DOCK-NORTH", "B-12") is SpatialRelation.원거리


def test_인접_거리_설정이_반영된다():
    wide = GridConflictMatrix(grid_cols=6, adjacency_distance=2)
    assert wide.relation("B-10", "B-12") is SpatialRelation.인접구역
    narrow = GridConflictMatrix(grid_cols=6, adjacency_distance=1)
    assert narrow.relation("B-10", "B-12") is SpatialRelation.원거리


def test_설정에서_생성된다(config):
    matrix = GridConflictMatrix.from_config(config)
    assert matrix.grid_cols == config["data_gen"]["yard"]["grid_cols"]


def test_미구현_전략은_명시적으로_실패한다(config):
    broken = {**config, "conflict_matrix": {**config["conflict_matrix"], "strategy": "polygon"}}
    with pytest.raises(NotImplementedError):
        GridConflictMatrix.from_config(broken)
