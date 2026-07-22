"""코퍼스 청크 → FAISS 인덱스 — 명세 §6.2.

명세 §6.2에 따라 **법령과 사고사례를 분리 인덱싱**한다. 각각 top-k를 따로
뽑아 근거로 쓰기 때문에, 한 인덱스에 섞으면 사례가 법령 자리를 차지하는
일이 생긴다.

    python -m retrieval.index_builder all

인덱스 종류:
    legal.faiss  + legal.meta.jsonl
    cases.faiss  + cases.meta.jsonl
    <name>.manifest.json   빌드 조건 기록 (모델·차원·건수)

manifest를 남기는 이유는 searcher가 "이 인덱스가 지금 모델과 맞는가"를
확인할 수 있게 하려는 것이다. 다른 모델로 만든 인덱스를 검색하면 에러 없이
무의미한 결과가 나온다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from config_loader import load_config, resolve
from retrieval.embedder import Embedder

MANIFEST_VERSION = 1


def load_chunks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"청크 파일이 없다: {path}\n먼저 실행: python -m retrieval.corpus_fetcher all"
        )
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"청크가 비어 있다: {path}")

    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: 중복 id가 있다. 인덱스 위치와 원문이 어긋난다.")
    return rows


def _embedding_text(chunk: dict[str, Any]) -> str:
    """임베딩 대상 텍스트.

    제목을 본문 앞에 붙인다. 법령은 조문 제목("화재위험작업 시의 준수사항")이
    본문보다 검색 질의와 더 잘 맞는 경우가 많고, 사례도 제목이 사고 유형을
    압축하고 있기 때문이다.
    """
    title = (chunk.get("title") or "").strip()
    text = (chunk.get("text") or "").strip()
    return f"{title}\n{text}" if title else text


class VectorCache:
    """청크 id로 임베딩 벡터를 캐시한다.

    CPU 임베딩은 1,800건에 1시간 반이 걸린다. 이 시간을 지키기 위한 장치다.

    id 기준이라 두 가지가 공짜로 된다:
      1. 중단 후 재개 — 체크포인트 이후 것만 다시 계산한다.
      2. 코퍼스 증분 확장 — 나중에 건설업 사례를 추가해도 기존 조선업·제조업
         벡터는 그대로 쓰고 새 것만 계산한다.

    파일:
        {name}.vectors.npy      (n, dim) float32
        {name}.vector_ids.json  벡터 행 순서와 1:1 대응하는 청크 id 목록
    """

    CHECKPOINT_EVERY = 128  # 이 건수마다 디스크에 저장

    def __init__(self, index_dir: Path, name: str, model_name: str) -> None:
        self.name = name
        self.model_name = model_name
        self.vectors_path = index_dir / f"{name}.vectors.npy"
        self.ids_path = index_dir / f"{name}.vector_ids.json"
        self._ids: list[str] = []
        self._vectors: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        if not (self.vectors_path.exists() and self.ids_path.exists()):
            return
        meta = json.loads(self.ids_path.read_text(encoding="utf-8"))
        if meta.get("model") != self.model_name:
            print(f"[{self.name}] 캐시가 다른 모델('{meta.get('model')}')로 만들어져 무시한다")
            return
        vectors = np.load(self.vectors_path)
        ids = meta.get("ids", [])
        if len(ids) != vectors.shape[0]:
            print(f"[{self.name}] 캐시 손상(id {len(ids)} vs 벡터 {vectors.shape[0]}) — 무시한다")
            return
        self._ids, self._vectors = ids, vectors.astype(np.float32, copy=False)
        print(f"[{self.name}] 벡터 캐시 로드: {len(ids)}건")

    def clear(self) -> None:
        self._ids, self._vectors = [], None
        for p in (self.vectors_path, self.ids_path):
            p.unlink(missing_ok=True)
        print(f"[{self.name}] 캐시 삭제 (--force)")

    def _save(self) -> None:
        if self._vectors is None:
            return
        # 임시 파일에 쓴 뒤 교체한다. 저장 도중에 죽어도 기존 캐시가 남는다.
        tmp_vec = self.vectors_path.with_name(self.vectors_path.name + ".tmp")
        # 파일 객체에 저장한다. np.save()에 경로를 넘기면 이름이 '.npy'로
        # 끝나지 않을 때 확장자를 멋대로 덧붙여서, 뒤따르는 replace()가
        # 없는 파일을 가리키게 된다.
        with tmp_vec.open("wb") as f:
            np.save(f, self._vectors)
        tmp_vec.replace(self.vectors_path)

        tmp_ids = self.ids_path.with_suffix(".json.tmp")
        tmp_ids.write_text(
            json.dumps({"model": self.model_name, "ids": self._ids}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_ids.replace(self.ids_path)

    def _append(self, ids: list[str], vectors: np.ndarray) -> None:
        self._ids.extend(ids)
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])

    def embed_missing(self, chunks: list[dict[str, Any]], embedder: Embedder) -> np.ndarray:
        """캐시에 없는 청크만 임베딩하고, 청크 순서대로 정렬한 행렬을 돌려준다."""
        known = {cid: i for i, cid in enumerate(self._ids)}
        missing = [c for c in chunks if c["id"] not in known]

        if missing:
            done = len(chunks) - len(missing)
            print(f"[{self.name}] 임베딩 대상 {len(missing)}건 "
                  f"(캐시 재사용 {done}건 / 전체 {len(chunks)}건), 모델 {embedder.model_name}")
            for start in range(0, len(missing), self.CHECKPOINT_EVERY):
                slice_ = missing[start:start + self.CHECKPOINT_EVERY]
                vectors = embedder.encode([_embedding_text(c) for c in slice_], show_progress=True)
                self._append([c["id"] for c in slice_], vectors)
                self._save()
                total_done = len(self._ids)
                print(f"[{self.name}] 체크포인트 {min(start + len(slice_), len(missing))}"
                      f"/{len(missing)} (캐시 누적 {total_done}건)", flush=True)
            known = {cid: i for i, cid in enumerate(self._ids)}
        else:
            print(f"[{self.name}] 전부 캐시에 있다 ({len(chunks)}건) — 임베딩 생략")

        assert self._vectors is not None
        return np.ascontiguousarray(self._vectors[[known[c["id"]] for c in chunks]])


def write_faiss_index(index, path: Path) -> None:
    """FAISS 인덱스를 파이썬 파일 IO로 저장한다.

    faiss.write_index()를 쓰지 않는 이유: 그 함수는 C++ fopen에 경로를 넘기는데,
    Windows에서 경로에 비ASCII 문자(예: 'C:\\...\\빅프\\...')가 있으면 ANSI
    코드페이지 변환에 걸려 실패한다. 실제로 이 프로젝트에서
    "could not open ... for writing: No such file or directory" 로 죽었고,
    디렉터리는 멀쩡히 존재했다.

    serialize_index()는 바이트 배열만 돌려주므로 파일 쓰기는 파이썬이 맡는다.
    파이썬은 유니코드 경로를 정상 처리한다.
    """
    import faiss

    path.write_bytes(faiss.serialize_index(index).tobytes())


def build_index(
    name: str,
    config: dict[str, Any],
    embedder: Embedder,
    force: bool = False,
) -> dict[str, Any]:
    import faiss  # numpy 이후에 로드된다 (retrieval/__init__.py 참고)

    spec = config["retrieval"]["indexes"][name]
    chunks_dir = resolve(config["paths"]["corpus_chunks"])
    index_dir = resolve(config["paths"]["corpus_index"])
    index_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks(chunks_dir / spec["chunks"])

    cache = VectorCache(index_dir, name, embedder.model_name)
    if force:
        cache.clear()

    started = time.time()
    vectors = cache.embed_missing(chunks, embedder)
    elapsed = time.time() - started

    if vectors.shape[0] != len(chunks):
        raise RuntimeError(f"[{name}] 임베딩 개수 불일치: {vectors.shape[0]} != {len(chunks)}")

    dim = int(vectors.shape[1])
    # 정규화된 벡터의 내적 = 코사인 유사도.
    # 청크가 1만 건 이하라 완전탐색(IndexFlatIP)이 충분히 빠르고 정확하다.
    # 근사 인덱스(IVF/HNSW)는 재현성만 떨어뜨린다.
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    write_faiss_index(index, index_dir / spec["index"])

    # 메타는 인덱스 위치 순서와 1:1로 맞춘다. 검색 결과의 정수 위치로 되찾는다.
    meta_path = index_dir / spec["meta"]
    with meta_path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "name": name,
        "model": embedder.model_name,
        "dimension": dim,
        "count": len(chunks),
        "max_seq_length": embedder.max_seq_length,
        "normalized": embedder.normalize,
        "metric": "inner_product",
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (index_dir / f"{name}.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if elapsed:
        rate = len(chunks) / elapsed
        print(f"[{name}] 완료: {len(chunks)}건 / {dim}차원 / {elapsed/60:.1f}분 ({rate:.1f}건/초)")
    else:
        print(f"[{name}] 완료: {len(chunks)}건 / {dim}차원 (캐시된 벡터 사용)")
    return manifest


def main() -> int:
    config = load_config()
    names = list(config["retrieval"]["indexes"])

    parser = argparse.ArgumentParser(description="FAISS 인덱스 구축 (명세 §6.2)")
    parser.add_argument("target", choices=[*names, "all"])
    parser.add_argument(
        "--force", action="store_true",
        help="캐시된 벡터를 무시하고 다시 임베딩한다 (모델이나 청크를 바꿨을 때)",
    )
    args = parser.parse_args()

    selected = names if args.target == "all" else [args.target]
    embedder = Embedder.from_config(config)

    for name in selected:
        try:
            build_index(name, config, embedder, force=args.force)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[{name}] 실패: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
