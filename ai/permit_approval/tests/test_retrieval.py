"""Retrieval 검증 — 명세 §6.2.

임베딩 모델 로딩(2.2GB)이 필요한 테스트는 인덱스가 실제로 구축된 경우에만
돌린다. 인덱스 없이도 돌아가는 순수 로직(쿼리 조립, 매니페스트 검증, 오류
처리)은 항상 검증한다.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from config_loader import load_config, resolve
from retrieval.index_builder import _embedding_text, load_chunks
from retrieval.searcher import IndexNotBuilt, Searcher, build_query
from schemas.permit import (
    AreaType,
    PermitRequest,
    Severity,
    SpecialConditions,
    TimeWindow,
    Violation,
    WorkType,
    Zone,
)


def _permit(**overrides) -> PermitRequest:
    base = dict(
        permit_id="PTW-TEST-1",
        work_type=WorkType.화기작업,
        zone=Zone(block_id="B-12", area_type=AreaType.탱크),
        time_window=TimeWindow(
            start=datetime(2026, 7, 22, 9), end=datetime(2026, 7, 22, 12)
        ),
        worker_count=3,
        work_description="선체 외판 용접 작업",
        special_conditions=SpecialConditions(adjacent_flammable=True),
    )
    base.update(overrides)
    return PermitRequest(**base)


def _index_ready(name: str) -> bool:
    config = load_config()
    spec = config["retrieval"]["indexes"][name]
    d = resolve(config["paths"]["corpus_index"])
    return (d / spec["index"]).exists() and (d / f"{name}.manifest.json").exists()


needs_index = pytest.mark.skipif(
    not (_index_ready("legal") and _index_ready("cases")),
    reason="인덱스 미구축 - python -m retrieval.index_builder all 먼저 실행",
)


# ----------------------------------------------------------- 인덱스 불필요

def test_쿼리에_작업정보와_위반요약이_모두_들어간다():
    """위반 요약이 빠지면 '용접 작업' 수준의 일반 문서만 걸린다."""
    violations = [Violation(
        rule_id="HARD-003", severity=Severity.hard,
        summary="인접 인화물이 존재하는 상태에서 환기 없이 화기작업을 신청했다.",
    )]
    query = build_query(_permit(), violations)

    assert "화기작업" in query
    assert "탱크" in query
    assert "선체 외판 용접 작업" in query
    assert "인접 인화물" in query


def test_위반이_없어도_쿼리가_만들어진다():
    query = build_query(_permit(), [])
    assert "화기작업" in query
    assert query.strip()


def test_설명이_비어도_쿼리가_비지_않는다():
    query = build_query(_permit(work_description=""), [])
    assert query.strip()


def test_임베딩_텍스트는_제목을_앞에_붙인다():
    chunk = {"title": "제241조(화재위험작업 시의 준수사항)", "text": "본문 내용"}
    out = _embedding_text(chunk)
    assert out.startswith("제241조")
    assert "본문 내용" in out


def test_제목이_없으면_본문만_쓴다():
    assert _embedding_text({"title": "", "text": "본문"}) == "본문"


def test_인덱스가_없으면_명확히_실패한다(tmp_path, monkeypatch):
    """조용히 빈 결과를 내면 4단계가 동작하는 줄 착각하게 된다."""
    config = load_config()
    broken = {**config, "paths": {**config["paths"], "corpus_index": str(tmp_path)}}
    searcher = Searcher("legal", broken)
    with pytest.raises(IndexNotBuilt, match="index_builder"):
        _ = searcher.manifest


def test_중복_id_청크는_인덱싱을_거부한다(tmp_path):
    """인덱스 위치와 원문이 어긋나면 검색 결과가 엉뚱한 문서를 가리킨다."""
    import json

    path = tmp_path / "dup.jsonl"
    rows = [
        {"id": "A", "source": "s", "title": "t", "text": "x", "legal_ref": None},
        {"id": "A", "source": "s", "title": "t", "text": "y", "legal_ref": None},
    ]
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="중복 id"):
        load_chunks(path)


def test_청크_파일이_없으면_안내한다(tmp_path):
    with pytest.raises(FileNotFoundError, match="corpus_fetcher"):
        load_chunks(tmp_path / "없는파일.jsonl")


# ----------------------------------------------------------- 인덱스 필요

@needs_index
def test_매니페스트가_실제_인덱스와_일치한다():
    for name in ("legal", "cases"):
        s = Searcher(name)
        assert s.manifest["dimension"] == s.index.d
        assert s.index.ntotal == s.manifest["count"] == len(s.meta)


@needs_index
def test_법령_검색이_관련_조문을_찾는다():
    hits = Searcher("legal").search("밀폐공간 작업 전 산소 및 유해가스 농도 측정", top_k=5)
    assert hits
    refs = " ".join(h.legal_ref or "" for h in hits)
    assert "제619조의2" in refs or "제620조" in refs, f"찾은 조문: {refs}"


@needs_index
def test_사례_검색이_관련_사고를_찾는다():
    hits = Searcher("cases").search("용접 작업 중 화재 폭발", top_k=5)
    assert hits
    blob = " ".join(h.title + h.text for h in hits)
    assert any(k in blob for k in ("화재", "폭발", "용접", "화기")), "관련 없는 사례만 검색됨"


@needs_index
def test_점수가_내림차순이고_코사인_범위_안에_있다():
    hits = Searcher("legal").search("화기작업 인화물", top_k=10)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    # 정규화 벡터의 내적이므로 [-1, 1]
    assert all(-1.01 <= s <= 1.01 for s in scores), scores


@needs_index
def test_top_k가_지켜진다():
    assert len(Searcher("legal").search("안전", top_k=3)) == 3


@needs_index
def test_빈_쿼리는_빈_결과():
    assert Searcher("legal").search("   ") == []


@needs_index
def test_법령과_사례가_분리_인덱싱되어_있다():
    """명세 §6.2: 섞으면 사례가 법령 자리를 차지한다."""
    legal = Searcher("legal").search("추락 재해", top_k=5)
    cases = Searcher("cases").search("추락 재해", top_k=5)

    assert all(h.legal_ref for h in legal), "법령 인덱스에 조문 근거 없는 항목이 있다"
    assert all(h.legal_ref is None for h in cases), "사례 인덱스에 법령이 섞였다"
    assert {h.chunk_id for h in legal}.isdisjoint({h.chunk_id for h in cases})


@needs_index
def test_허가서로_법령과_사례를_함께_검색한다():
    from retrieval.searcher import PermitRetriever

    violations = [Violation(
        rule_id="HARD-003", severity=Severity.hard,
        summary="인접 인화물이 존재하는 상태에서 환기 없이 화기작업을 신청했다.",
    )]
    result = PermitRetriever().retrieve(_permit(), violations)

    assert result["legal"] and result["cases"]
    assert len(result["cases"]) <= load_config()["retrieval"]["top_k_cases"]


@needs_index
def test_룰이_지정한_근거_조문은_반드시_컨텍스트에_들어간다():
    """5단계 인용 검증(명세 §6.3)의 전제 조건.

    의미 검색만 쓰면 룰의 근거 조문이 top-5에 들어오는 비율이 16%에 그친다.
    그 상태로 생성기에 넘기면 정작 그 판정의 법적 근거를 인용할 수 없다.
    """
    from retrieval.searcher import PermitRetriever, normalize_legal_ref

    ref = "산업안전보건기준에 관한 규칙 제241조(화재위험작업 시의 준수사항)"
    violations = [Violation(
        rule_id="HARD-003", severity=Severity.hard,
        summary="인접 인화물이 존재하는 상태에서 환기 없이 화기작업을 신청했다.",
        legal_basis=ref,
    )]
    result = PermitRetriever().retrieve(_permit(), violations)

    refs = [h.legal_ref for h in result["legal"]]
    assert normalize_legal_ref(ref) in refs, f"근거 조문 누락. 받은 것: {refs}"

    injected = [h for h in result["legal"] if h.matched_by == "rule"]
    assert len(injected) == 1
    assert injected[0].legal_ref == normalize_legal_ref(ref)


@needs_index
def test_근거_조문은_중복되지_않는다():
    """같은 조문을 인용하는 위반이 여럿이어도 컨텍스트에 한 번만 들어간다."""
    from retrieval.searcher import PermitRetriever

    ref = "산업안전보건기준에 관한 규칙 제241조(화재위험작업 시의 준수사항)"
    violations = [
        Violation(rule_id="HARD-003", severity=Severity.hard, summary="a", legal_basis=ref),
        Violation(rule_id="SIMOPS-004", severity=Severity.hard, summary="b", legal_basis=ref),
    ]
    result = PermitRetriever().retrieve(_permit(), violations)
    ids = [h.chunk_id for h in result["legal"]]
    assert len(ids) == len(set(ids))


@needs_index
def test_존재하지_않는_조문을_인용하면_조용히_무시된다():
    """룰 YAML에 오타가 나도 검색이 죽지는 않아야 한다.

    (조문 실재 여부 자체는 tools/verify_legal_refs.py가 따로 검사한다.)
    """
    from retrieval.searcher import PermitRetriever

    violations = [Violation(
        rule_id="X", severity=Severity.hard, summary="a",
        legal_basis="산업안전보건기준에 관한 규칙 제99999조(없는 조문)",
    )]
    result = PermitRetriever().retrieve(_permit(), violations)
    assert result["legal"]
    assert all(h.matched_by == "semantic" for h in result["legal"])


@needs_index
def test_조문을_번호로_정확히_꺼낸다():
    from retrieval.searcher import Searcher

    s = Searcher("legal")
    hit = s.fetch_by_legal_ref("산업안전보건기준에 관한 규칙 제241조(화재위험작업 시의 준수사항)")
    assert hit is not None
    assert hit.legal_ref == "산업안전보건기준에 관한 규칙 제241조"
    assert hit.matched_by == "rule"
    assert s.fetch_by_legal_ref("산업안전보건기준에 관한 규칙 제99999조") is None
