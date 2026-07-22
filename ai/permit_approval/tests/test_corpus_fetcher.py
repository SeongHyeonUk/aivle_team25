"""코퍼스 수집기 검증 — 명세 §7.

인증키가 없으므로 네트워크를 타지 않는 부분만 검증한다:
파싱 로직, 청크 스키마, 키 부재 시 동작.
TODO(팀확인): 키 발급 후 실제 응답으로 통합 테스트 추가.
"""

from __future__ import annotations

import pytest

from retrieval.corpus_fetcher import (
    MissingCredential,
    _flatten_article_text,
    _iter_case_items,
    _write_chunks,
    fetch_law_articles,
)


def test_키가_없으면_조용히_실패하지_않는다(config, monkeypatch):
    """빈 코퍼스를 만들고 넘어가면 4단계에서 검색이 조용히 0건을 반환한다."""
    monkeypatch.delenv("LAW_OC", raising=False)
    with pytest.raises(MissingCredential) as exc:
        fetch_law_articles("산업안전보건기준에 관한 규칙", config)

    # 무엇을 어디서 받아야 하는지 안내가 들어 있어야 한다.
    assert "open.law.go.kr" in str(exc.value)


def test_조문_본문과_항호가_하나로_합쳐진다():
    article = {
        "조문번호": "241",
        "조문제목": "화재위험작업 시의 준수사항",
        "조문내용": "제241조(화재위험작업 시의 준수사항) 사업주는 다음 각 호를 준수하여야 한다.",
        "항": [
            {
                "항내용": "① 작업 준비 및 작업 절차 수립",
                "호": [{"호내용": "1. 화기감시자 배치"}, {"호내용": "2. 가연물 제거"}],
            }
        ],
    }
    text = _flatten_article_text(article)
    assert "화재위험작업" in text
    assert "화기감시자 배치" in text
    assert "가연물 제거" in text


def test_단일_항이_dict로_와도_처리된다():
    """공공 API는 원소가 1개일 때 리스트 대신 dict를 준다. 흔한 함정이다."""
    article = {"조문내용": "본문", "항": {"항내용": "① 단일 항", "호": {"호내용": "1. 단일 호"}}}
    text = _flatten_article_text(article)
    assert "단일 항" in text
    assert "단일 호" in text


def test_빈_조문은_빈_문자열을_낸다():
    assert _flatten_article_text({}) == ""


def test_응답_항목_추출_표준경로():
    payload = {"response": {"body": {"items": {"item": [{"title": "A"}, {"title": "B"}]}}}}
    assert [i["title"] for i in _iter_case_items(payload)] == ["A", "B"]


def test_응답_항목이_하나여도_추출된다():
    payload = {"response": {"body": {"items": {"item": {"title": "A"}}}}}
    assert [i["title"] for i in _iter_case_items(payload)] == ["A"]


def test_빈_응답은_빈_목록():
    assert list(_iter_case_items({"response": {"body": {}}})) == []


def test_청크_스키마_위반은_거부된다(tmp_path):
    """명세 §7이 고정한 스키마를 벗어난 청크가 인덱스에 들어가면 안 된다."""
    with pytest.raises(ValueError, match="스키마 위반"):
        _write_chunks(tmp_path / "x.jsonl", [{"id": "A", "source": "S", "title": "T"}])


def test_중복_id는_거부된다(tmp_path):
    """중복 id는 검색 결과가 엉뚱한 원문을 가리키게 만들면서도 에러가 안 난다.

    실제로 법제처 응답의 편·장·절 제목 행이 다음 조문의 번호를 달고 오는 바람에
    1065행 중 190행이 중복됐던 적이 있다. 그 재발을 막는 방어선이다.
    """
    base = {"source": "S", "title": "T", "text": "본문", "legal_ref": None}
    with pytest.raises(ValueError, match="중복 청크 id"):
        _write_chunks(tmp_path / "x.jsonl", [{"id": "A", **base}, {"id": "A", **base}])


def test_정상_청크는_jsonl로_기록된다(tmp_path):
    import json

    path = tmp_path / "legal.jsonl"
    _write_chunks(path, [{
        "id": "LAW-1", "source": "규칙", "title": "제241조",
        "text": "본문", "legal_ref": "규칙 제241조",
    }])
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["legal_ref"] == "규칙 제241조"
