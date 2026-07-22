"""블록 인접 관계 판정 — 명세 §6.1.

데모용은 단순 그리드로 시작한다. `block_id`가 "B-12" 형태라고 보고
접두사(구역)와 일련번호를 파싱해 (row, col)로 환산한 뒤 체비쇼프 거리로
인접 여부를 본다.

TODO(팀확인): 실제 야드 배치도. 확보되면 `AdjacencyResolver` 프로토콜을
구현하는 새 클래스(예: DB의 blocks.grid_x/grid_y를 읽는 로더)로 갈아끼우면
engine.py는 손대지 않아도 된다.
"""

from __future__ import annotations

import re
from typing import Protocol

from schemas.permit import SpatialRelation

_BLOCK_RE = re.compile(r"^(?P<prefix>[A-Za-z]+)-(?P<index>\d+)$")


class AdjacencyResolver(Protocol):
    """블록 두 개의 공간 관계를 판정한다."""

    def relation(self, block_a: str, block_b: str) -> SpatialRelation: ...


class GridConflictMatrix:
    """일련번호를 행·열로 펼치는 격자 배치 가정.

    B-1 .. B-6 이 첫 행, B-7 .. B-12 가 둘째 행 (grid_cols=6인 경우).
    """

    def __init__(
        self,
        grid_cols: int,
        adjacency_distance: int = 1,
        prefix_isolates: bool = True,
    ) -> None:
        if grid_cols < 1:
            raise ValueError("grid_cols는 1 이상이어야 한다")
        self.grid_cols = grid_cols
        self.adjacency_distance = adjacency_distance
        self.prefix_isolates = prefix_isolates

    @classmethod
    def from_config(cls, config: dict) -> GridConflictMatrix:
        cm = config.get("conflict_matrix", {})
        strategy = cm.get("strategy", "grid")
        if strategy != "grid":
            raise NotImplementedError(
                f"conflict_matrix.strategy='{strategy}'는 아직 구현되지 않았다. "
                "실제 야드 배치도 확보 후 리졸버를 추가할 것."
            )
        return cls(
            grid_cols=config.get("data_gen", {}).get("yard", {}).get("grid_cols", 6),
            adjacency_distance=cm.get("adjacency_distance", 1),
            prefix_isolates=cm.get("prefix_isolates", True),
        )

    def _coords(self, block_id: str) -> tuple[str, int, int] | None:
        """block_id를 (접두사, row, col)로 파싱. 형식이 안 맞으면 None."""
        m = _BLOCK_RE.match(block_id.strip())
        if not m:
            return None
        index = int(m.group("index")) - 1  # 1-based → 0-based
        if index < 0:
            return None
        return m.group("prefix").upper(), index // self.grid_cols, index % self.grid_cols

    def relation(self, block_a: str, block_b: str) -> SpatialRelation:
        if block_a.strip().upper() == block_b.strip().upper():
            return SpatialRelation.동일구역

        a, b = self._coords(block_a), self._coords(block_b)
        if a is None or b is None:
            # 파싱 불가한 식별자는 인접을 주장할 근거가 없다. 안전 측면에서는
            # 인접으로 보는 게 보수적이지만, 그러면 무관한 블록끼리 전부
            # 오탐이 난다. 명세 §10의 "정상 케이스 오탐 0" 목표를 우선한다.
            return SpatialRelation.원거리

        prefix_a, row_a, col_a = a
        prefix_b, row_b, col_b = b

        if prefix_a != prefix_b and self.prefix_isolates:
            # 접두사가 다른 구역 간의 실제 배치 관계는 아직 모른다.
            # TODO(팀확인): 실제 배치도가 오면 구역 간 인접도 판정해야 한다.
            return SpatialRelation.원거리

        distance = max(abs(row_a - row_b), abs(col_a - col_b))
        if distance <= self.adjacency_distance:
            return SpatialRelation.인접구역
        return SpatialRelation.원거리
