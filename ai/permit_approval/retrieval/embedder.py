"""bge-m3 임베딩 래퍼 — 명세 §6.2.

이 모듈은 **학습하지 않는다.** 사전학습 모델 추론만 한다 (명세 §11).

첫 실행 시 HuggingFace에서 모델(약 2.2GB)을 내려받아 캐시한다.
기본 캐시 위치: ~/.cache/huggingface
"""

from __future__ import annotations

import functools
from typing import Any, Sequence

import numpy as np

from config_loader import load_config


class Embedder:
    """SentenceTransformer 래퍼. 모델은 처음 쓸 때 로드한다.

    지연 로딩하는 이유: config만 읽으면 되는 테스트나 CLI가 2.2GB 모델 로딩을
    기다리지 않아도 되게 하려는 것이다.
    """

    def __init__(
        self,
        model_name: str,
        max_seq_length: int = 512,
        batch_size: int = 16,
        normalize: bool = True,
    ) -> None:
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self.batch_size = batch_size
        self.normalize = normalize
        self._model = None

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> Embedder:
        config = config or load_config()
        r = config["retrieval"]
        return cls(
            model_name=r["embedding_model"],
            max_seq_length=r.get("max_seq_length", 512),
            batch_size=r.get("batch_size", 16),
            normalize=r.get("normalize", True),
        )

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.model_name)
            # bge-m3 기본값은 8192다. 줄이지 않으면 CPU 추론이 크게 느려진다.
            model.max_seq_length = self.max_seq_length
            self._model = model
        return self._model

    @property
    def dimension(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    def encode(
        self,
        texts: Sequence[str],
        show_progress: bool = False,
    ) -> np.ndarray:
        """문장 목록 → (n, dim) float32 배열.

        bge-m3는 쿼리·문서에 별도 지시문(instruction prefix)을 붙이지 않는다.
        e5 계열로 교체한다면 "query: " / "passage: " 접두사가 필요하다.
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        vectors = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        """단일 텍스트 → (1, dim). 검색 쿼리용."""
        return self.encode([text])


@functools.lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """프로세스당 하나만 만든다. 모델을 두 번 로드하면 메모리가 두 배 든다."""
    return Embedder.from_config()
