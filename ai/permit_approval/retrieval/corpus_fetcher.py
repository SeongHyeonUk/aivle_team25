"""코퍼스 수집 — 명세 §7.

명세 §7의 `TODO(팀확인): 각 소스의 접근 방법(API/크롤링/수동)과 라이선스 확인`
에 대한 조사 결과:

  1. 산업안전보건기준에 관한 규칙
     → 국가법령정보 공동활용 OPEN API (https://open.law.go.kr)
       공공저작물. 인증값(OC) 신청 필요. law.go.kr robots.txt는 Allow: /
  2. KOSHA GUIDE / 안전보건법령
     → 공공데이터포털 15123696 안전보건법령 스마트검색
       **이용허락범위 제한 없음**. 개발계정 10,000건/일
  3. 중대재해·재해사례
     → 공공데이터포털 15121001 국내재해사례 게시판 정보 조회서비스
       **이용허락범위 제한 없음**. 개발계정 자동승인, 1,000건/일
       business 파라미터로 조선업 필터 가능

세 소스 모두 공식 API로 제공되므로 **웹 크롤러를 만들지 않는다.** 스크래핑은
법적 리스크와 유지보수 부담만 늘리고 얻는 게 없다.

--- 실행 전 준비 (사람이 해야 함) ---
.env.example을 .env로 복사하고 LAW_OC / DATA_GO_KR_SERVICE_KEY를 채운다.
키 없이 실행하면 무엇을 어디서 받아야 하는지 안내하고 종료한다.

--- 이 파일의 상태 ---
MVP(§9의 1~3단계) 범위 밖이다. 코드는 갖췄지만 인증키가 없어 아직 실전
응답으로 검증되지 않았다. 특히 응답 JSON의 필드명은 각 API의 공식 활용가이드
문서와 대조가 필요하다 — 아래 TODO(팀확인) 표시를 참고할 것.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import requests

from config_loader import load_config, resolve

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv 미설치 시 환경변수만 사용
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


SETUP_GUIDE = """
인증키가 설정되지 않았습니다.

1) {name} 발급
{steps}

2) 이 디렉터리의 .env.example을 .env로 복사한 뒤 값을 채우세요.

키가 없어도 MVP(스키마·합성데이터·룰엔진)는 정상 동작합니다.
코퍼스는 명세 §9의 4단계(Retrieval)에서만 필요합니다.
"""

LAW_STEPS = """   - https://open.law.go.kr/LSO/openApi/cuAskList.do 에서 OPEN API 신청
   - 승인 후 발급되는 OC 값(보통 이메일 아이디의 @ 앞부분)을 LAW_OC에 입력"""

DATA_GO_KR_STEPS = """   - https://www.data.go.kr 회원가입
   - '한국산업안전보건공단_국내재해사례 게시판 정보 조회서비스'(15121001) 활용신청
     (개발계정은 자동승인)
   - 마이페이지의 일반 인증키(Decoding)를 DATA_GO_KR_SERVICE_KEY에 입력"""


class MissingCredential(RuntimeError):
    """인증키 부재. 조용히 실패하지 않고 안내와 함께 터뜨린다."""


def _require(env_key: str, name: str, steps: str) -> str:
    value = os.environ.get(env_key, "").strip()
    if not value:
        raise MissingCredential(SETUP_GUIDE.format(name=name, steps=steps))
    return value


def _save_raw(raw_dir: Path, filename: str, payload: Any) -> None:
    """응답 원문을 그대로 보존한다 (명세 §7: 수집 → 청킹 순서)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / filename
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")


def _write_chunks(path: Path, chunks: list[dict[str, Any]]) -> None:
    """청크 스키마는 명세 §7이 고정한다: {id, source, title, text, legal_ref}."""
    required = {"id", "source", "title", "text", "legal_ref"}
    for chunk in chunks:
        missing = required - chunk.keys()
        if missing:
            raise ValueError(f"청크 스키마 위반 - 누락 필드 {missing}: {chunk.get('id')}")

    # id는 인덱스에서 청크를 되찾는 열쇠다. 중복되면 검색 결과가 엉뚱한 원문을
    # 가리키고, 그 상태로도 아무 에러 없이 동작한다 — 반드시 여기서 막는다.
    ids = [c["id"] for c in chunks]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        dupes = sorted({i for i in ids if i in seen or seen.add(i)})
        raise ValueError(
            f"중복 청크 id {len(dupes)}종 (예: {dupes[:5]}). "
            "원문 파싱 로직을 확인할 것."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
# 1. 법령 — 국가법령정보 공동활용 OPEN API
# --------------------------------------------------------------------------

def _flatten_article_text(article: dict[str, Any]) -> str:
    """조문 본문 + 항/호를 하나의 텍스트로 합친다.

    임베딩 검색 단위가 조문이므로(명세 §6.2) 항·호를 분리하지 않는다.
    """
    parts: list[str] = []
    body = article.get("조문내용")
    if body:
        parts.append(str(body).strip())

    clauses = article.get("항") or []
    if isinstance(clauses, dict):
        clauses = [clauses]
    for clause in clauses:
        text = clause.get("항내용")
        if text:
            parts.append(str(text).strip())
        items = clause.get("호") or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            item_text = item.get("호내용")
            if item_text:
                parts.append(str(item_text).strip())
    return "\n".join(p for p in parts if p)


def fetch_law_articles(law_name: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """법령 하나를 조문 단위 청크로 변환한다."""
    src = config["corpus_sources"]["law_go_kr"]
    oc = _require("LAW_OC", "국가법령정보 OPEN API 인증값(OC)", LAW_STEPS)

    response = requests.get(
        src["service_endpoint"],
        params={"OC": oc, "target": "law", "type": "JSON", "LM": law_name},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    _save_raw(resolve(config["paths"]["corpus_raw"]), f"law_{law_name}.json", payload)

    # TODO(팀확인): 응답 구조를 실제 키로 검증할 것. 아래는 공식 가이드 기준 경로다.
    root = payload.get("법령", payload)
    articles = root.get("조문", {}).get("조문단위", [])
    if isinstance(articles, dict):
        articles = [articles]

    chunks = []
    for article in articles:
        # 응답에는 편·장·절 제목 행("제1편 총칙")이 섞여 있는데, 이들은 바로 다음
        # 조문의 조문번호를 그대로 달고 온다. 조문번호 유무로 거르면 중복 id가
        # 생긴다(실측: 1065행 중 190행 중복). API가 주는 조문여부 플래그로 거른다.
        #   조문여부 = "조문"(실제 조문) | "전문"(편·장·절 제목)
        if article.get("조문여부") != "조문":
            continue

        number = article.get("조문번호")
        if not number:
            continue
        text = _flatten_article_text(article)
        if not text:
            continue

        branch = article.get("조문가지번호")
        ref = f"제{number}조" + (f"의{branch}" if branch else "")
        title = article.get("조문제목") or ref

        chunks.append({
            "id": f"LAW-{law_name}-{ref}",
            "source": law_name,
            "title": f"{ref}({title})",
            "text": text,
            "legal_ref": f"{law_name} {ref}",
        })
    return chunks


def fetch_all_laws(config: dict[str, Any]) -> list[dict[str, Any]]:
    src = config["corpus_sources"]["law_go_kr"]
    chunks: list[dict[str, Any]] = []
    for i, law_name in enumerate(src["targets"]):
        if i:
            time.sleep(src["request_interval_sec"])
        found = fetch_law_articles(law_name, config)
        print(f"  {law_name}: 조문 {len(found)}건")
        chunks.extend(found)
    return chunks


# --------------------------------------------------------------------------
# 2. 재해사례 — 공공데이터포털 15121001
# --------------------------------------------------------------------------

def _iter_case_items(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """응답에서 항목을 꺼낸다.

    이 API는 공공데이터포털 표준과 달리 `response` 래퍼 없이 최상위에
    {header, body}를 준다(검증 완료). 표준형도 함께 지원해 둔다.
    """
    body = payload.get("response", {}).get("body", payload.get("body", {}))
    items = body.get("items", body.get("item", []))
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    yield from items or []


def _result_code(payload: dict[str, Any]) -> tuple[str, str]:
    header = payload.get("response", {}).get("header", payload.get("header", {}))
    return str(header.get("resultCode", "")), str(header.get("resultMsg", ""))


def fetch_accident_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    """재해사례를 사례 1건 단위 청크로 변환한다 (명세 §6.2).

    주의: 이 API는 business·keyword 요청 파라미터를 **무시한다**(실측 확인).
    어떤 값을 보내도 전체 목록이 오므로, 업종 필터는 응답의 business 필드로
    여기서 건다.
    """
    src = config["corpus_sources"]["kosha_cases"]
    service_key = _require(
        "DATA_GO_KR_SERVICE_KEY", "공공데이터포털 인증키", DATA_GO_KR_STEPS
    )
    raw_dir = resolve(config["paths"]["corpus_raw"])
    keep = set(src.get("keep_businesses") or [])

    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped = 0

    for page in range(1, src["max_pages"] + 1):
        response = requests.get(
            src["endpoint"],
            params={
                "serviceKey": service_key,
                "callApiId": src["call_api_id"],
                "pageNo": page,
                "numOfRows": src["num_of_rows"],
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        _save_raw(raw_dir, f"cases_p{page}.json", payload)

        code, msg = _result_code(payload)
        if code and code != "00":
            raise RuntimeError(f"재해사례 API 오류 (page {page}): resultCode={code} {msg}")

        items = list(_iter_case_items(payload))
        if not items:
            break  # 마지막 페이지

        for item in items:
            business = (item.get("business") or "").strip()
            if keep and business not in keep:
                skipped += 1
                continue

            board_no = item.get("boardno")
            text = (item.get("contents") or "").strip()
            title = (item.get("keyword") or "").strip()
            if not board_no or not text:
                continue
            if board_no in seen:  # 페이지 경계 중복 방어
                continue
            seen.add(board_no)

            chunks.append({
                "id": f"KOSHA-CASE-{board_no}",
                "source": f"KOSHA 국내재해사례({business})" if business else "KOSHA 국내재해사례",
                "title": title,
                "text": text,
                # 사례에는 조문 근거가 붙지 않는다. 스키마 통일을 위해 None.
                "legal_ref": None,
            })

        print(f"  page {page}: 누적 {len(chunks)}건" + (f" (업종 필터 제외 {skipped}건)" if skipped else ""))
        time.sleep(src["request_interval_sec"])

    return chunks


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    load_dotenv(resolve(".env"))
    config = load_config()
    chunks_dir = resolve(config["paths"]["corpus_chunks"])

    parser = argparse.ArgumentParser(description="코퍼스 수집 (명세 §7)")
    parser.add_argument(
        "source",
        choices=["law", "cases", "all"],
        help="law=법령 조문, cases=재해사례, all=둘 다",
    )
    args = parser.parse_args()

    # 명세 §6.2: 법령과 사고사례는 분리 인덱싱한다. 파일부터 나눠 둔다.
    jobs = {
        "law": ("법령 조문", fetch_all_laws, chunks_dir / "legal.jsonl"),
        "cases": ("재해사례", fetch_accident_cases, chunks_dir / "cases.jsonl"),
    }
    selected = ["law", "cases"] if args.source == "all" else [args.source]

    for key in selected:
        label, fetcher, out_path = jobs[key]
        print(f"[{label}] 수집 시작")
        try:
            chunks = fetcher(config)
        except MissingCredential as exc:
            print(exc, file=sys.stderr)
            return 1
        except requests.RequestException as exc:
            print(f"[{label}] 요청 실패: {exc}", file=sys.stderr)
            return 1
        _write_chunks(out_path, chunks)
        print(f"[{label}] 완료: {len(chunks)}건 -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
