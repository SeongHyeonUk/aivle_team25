"""top-k 검색 — 명세 §6.2.

허가서 내용(work_type + description + 위반 요약)을 쿼리로 임베딩해
법령·사례 인덱스에서 각각 top-k를 뽑는다.

이 모듈은 **판정에 관여하지 않는다.** 검색 결과는 5단계 RAG 생성기가
설명문을 쓸 때 인용할 근거일 뿐이고, verdict는 이미 룰엔진이 정한 뒤다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from config_loader import load_config, resolve
from retrieval.embedder import Embedder, get_embedder
from schemas.permit import PermitRequest, Violation


@dataclass(frozen=True)
class SearchHit:
    """검색 결과 1건."""

    chunk_id: str
    title: str
    text: str
    source: str
    legal_ref: str | None
    score: float
    # "semantic" = 임베딩 검색으로 올라옴
    # "rule"     = 룰엔진이 근거로 지정한 조문이라 무조건 주입됨
    matched_by: str = "semantic"

    def snippet(self, length: int = 200) -> str:
        body = " ".join(self.text.split())
        return body[:length] + ("…" if len(body) > length else "")


def normalize_legal_ref(ref: str) -> str:
    """'…제241조(화재위험작업 시의 준수사항)' -> '…제241조'.

    YAML의 legal_ref는 사람이 읽기 좋게 조문 제목을 괄호로 달고 있는데,
    코퍼스의 legal_ref는 조문 번호까지만이다.
    """
    return ref.split("(")[0].strip()


class IndexNotBuilt(RuntimeError):
    """인덱스 부재. 조용히 빈 결과를 내지 않고 명확히 알린다."""


class Searcher:
    """인덱스 하나에 대한 검색기."""

    def __init__(self, name: str, config: dict[str, Any] | None = None,
                 embedder: Embedder | None = None) -> None:
        self.name = name
        self.config = config or load_config()
        self._embedder = embedder
        spec = self.config["retrieval"]["indexes"][name]
        self.index_dir = resolve(self.config["paths"]["corpus_index"])
        self.index_path = self.index_dir / spec["index"]
        self.meta_path = self.index_dir / spec["meta"]
        self.manifest_path = self.index_dir / f"{name}.manifest.json"

    @property
    def embedder(self) -> Embedder:
        return self._embedder or get_embedder()

    @cached_property
    def manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            raise IndexNotBuilt(
                f"[{self.name}] 인덱스가 없다.\n"
                f"먼저 실행: python -m retrieval.index_builder {self.name}"
            )
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    @cached_property
    def meta(self) -> list[dict[str, Any]]:
        rows = [
            json.loads(line)
            for line in self.meta_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(rows) != self.manifest["count"]:
            raise IndexNotBuilt(
                f"[{self.name}] 메타({len(rows)})와 매니페스트({self.manifest['count']}) "
                "건수가 다르다. 인덱스를 다시 만들 것."
            )
        return rows

    @cached_property
    def index(self):
        import faiss  # numpy 이후 로드 (retrieval/__init__.py 참고)

        if not self.index_path.exists():
            raise IndexNotBuilt(
                f"[{self.name}] 인덱스 파일이 없다: {self.index_path}\n"
                f"먼저 실행: python -m retrieval.index_builder {self.name}"
            )
        # faiss.read_index()가 아니라 파이썬으로 읽는다. 이유는
        # index_builder.write_faiss_index()의 주석 참고 (한글 경로 문제).
        index = faiss.deserialize_index(
            np.frombuffer(self.index_path.read_bytes(), dtype=np.uint8)
        )

        # 다른 모델로 만든 인덱스를 검색하면 에러 없이 무의미한 결과가 나온다.
        # 조용한 오답이 가장 위험하므로 여기서 막는다.
        if index.d != self.manifest["dimension"]:
            raise IndexNotBuilt(
                f"[{self.name}] 차원 불일치: 인덱스 {index.d} vs 매니페스트 "
                f"{self.manifest['dimension']}"
            )
        if self.manifest["model"] != self.embedder.model_name:
            raise IndexNotBuilt(
                f"[{self.name}] 인덱스는 '{self.manifest['model']}'로 만들어졌는데 "
                f"현재 모델은 '{self.embedder.model_name}'다. 인덱스를 다시 만들 것."
            )
        if index.ntotal != len(self.meta):
            raise IndexNotBuilt(
                f"[{self.name}] 벡터 수({index.ntotal})와 메타 수({len(self.meta)})가 다르다."
            )
        return index

    @cached_property
    def _by_legal_ref(self) -> dict[str, dict[str, Any]]:
        return {
            normalize_legal_ref(row["legal_ref"]): row
            for row in self.meta
            if row.get("legal_ref")
        }

    def fetch_by_legal_ref(self, ref: str) -> SearchHit | None:
        """조문 번호로 정확히 하나를 꺼낸다. 없으면 None.

        의미 검색과 달리 결정론적이다. 룰엔진이 지정한 근거 조문을 컨텍스트에
        넣을 때 쓴다.
        """
        row = self._by_legal_ref.get(normalize_legal_ref(ref))
        if row is None:
            return None
        return SearchHit(
            chunk_id=row["id"],
            title=row.get("title", ""),
            text=row.get("text", ""),
            source=row.get("source", ""),
            legal_ref=row.get("legal_ref"),
            score=1.0,
            matched_by="rule",
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchHit]:
        if top_k is None:
            key = f"top_k_{self.name}"
            top_k = self.config["retrieval"].get(key, 5)
        if not query.strip():
            return []

        vector = self.embedder.encode_one(query)
        scores, positions = self.index.search(vector, min(top_k, self.index.ntotal))

        hits = []
        for score, pos in zip(scores[0], positions[0]):
            if pos < 0:  # FAISS는 결과가 모자라면 -1을 채운다
                continue
            row = self.meta[int(pos)]
            hits.append(SearchHit(
                chunk_id=row["id"],
                title=row.get("title", ""),
                text=row.get("text", ""),
                source=row.get("source", ""),
                legal_ref=row.get("legal_ref"),
                score=float(score),
            ))
        return hits


def build_query(permit: PermitRequest, violations: Sequence[Violation] = ()) -> str:
    """허가서와 위반 내용을 검색 쿼리 한 덩어리로 만든다 (명세 §6.2).

    위반 요약을 함께 넣는 게 핵심이다. 허가서 본문만으로는 "용접 작업"
    수준의 일반적인 문서가 걸리는데, "인접 인화물이 있는데 환기가 없다"는
    위반 요약이 들어가면 그 상황에 맞는 조문·사례가 올라온다.
    """
    parts = [
        permit.work_type.value,
        permit.zone.area_type.value,
        permit.work_description.strip(),
    ]
    parts.extend(v.summary for v in violations if v.summary)
    return "\n".join(p for p in parts if p)


class PermitRetriever:
    """법령·사례 인덱스를 함께 조회하는 상위 래퍼 (명세 §6.2의 분리 인덱싱)."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_config()
        embedder = get_embedder()
        self.legal = Searcher("legal", self.config, embedder)
        self.cases = Searcher("cases", self.config, embedder)

    def retrieve(
        self,
        permit: PermitRequest,
        violations: Sequence[Violation] = (),
    ) -> dict[str, list[SearchHit]]:
        """법령·사례 근거를 모아 돌려준다.

        법령 쪽은 두 경로를 합친다:
          1. 룰엔진이 근거로 지정한 조문 — 결정론적이라 **항상** 포함한다.
          2. 의미 검색 top-k — 룰이 짚지 못한 관련 조문을 보완한다.

        1번을 따로 주입하는 이유: 실측 결과 룰의 근거 조문이 의미 검색 top-5에
        들어오는 비율이 28.3%(60건 표본)에 그쳤다. 검색에만 맡기면 생성기의 컨텍스트에
        정작 그 판정의 법적 근거가 빠지고, 명세 §6.3의 인용 검증에서 룰의
        근거를 인용할 수 없게 된다. 규칙의 근거는 검색으로 '찾을' 대상이 아니라
        이미 정해진 사실이다.
        """
        query = build_query(permit, violations)

        cited: list[SearchHit] = []
        seen: set[str] = set()
        for violation in violations:
            if not violation.legal_basis:
                continue
            hit = self.legal.fetch_by_legal_ref(violation.legal_basis)
            if hit and hit.chunk_id not in seen:
                cited.append(hit)
                seen.add(hit.chunk_id)

        semantic = self.legal.search(query, self.config["retrieval"].get("top_k_legal", 5))
        legal = cited + [h for h in semantic if h.chunk_id not in seen]

        return {
            "legal": legal,
            "cases": self.cases.search(query, self.config["retrieval"].get("top_k_cases", 5)),
        }
