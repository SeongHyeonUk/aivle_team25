"""룰 YAML의 조문 번호를 수집한 실제 법령 코퍼스와 대조한다.

README와 YAML 주석에 적어둔 "legal_ref는 잠정값이며 4단계에서 교차 검증한다"의
그 검증이다. corpus/chunks/legal.jsonl이 있어야 실행된다.

    python -m tools.verify_legal_refs

- 존재하지 않는 조문을 인용하면 감사에서 방어할 수 없다 -> FAIL
- 조문은 있지만 제목이 다르면 오타이거나 개정으로 조문이 바뀐 것 -> WARN
"""

from __future__ import annotations

import json
import re
import sys

from config_loader import load_config, resolve
from rule_engine.engine import RuleEngine

# "산업안전보건기준에 관한 규칙 제619조의2(산소 및 유해가스 농도의 측정)"
REF_RE = re.compile(r"^(?P<law>.+?)\s+제(?P<num>\d+)조(?:의(?P<branch>\d+))?(?:\((?P<title>.+)\))?$")


def _load_corpus() -> dict[str, dict]:
    config = load_config()
    path = resolve(config["paths"]["corpus_chunks"]) / "legal.jsonl"
    if not path.exists():
        print(f"코퍼스가 없다: {path}\n먼저 실행: python -m retrieval.corpus_fetcher law", file=sys.stderr)
        raise SystemExit(2)
    corpus = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        corpus[row["legal_ref"]] = row
    return corpus


def main() -> int:
    corpus = _load_corpus()
    engine = RuleEngine.from_config()
    rules = [*engine.hard_rules, *engine.simops_rules]

    failures, warnings, ok = [], [], 0

    for rule in rules:
        rid = rule["rule_id"]
        ref = rule.get("legal_ref", "")
        m = REF_RE.match(ref.strip())
        if not m:
            failures.append((rid, ref, "형식을 해석할 수 없음"))
            continue

        law, num, branch = m["law"], m["num"], m["branch"]
        key = f"{law} 제{num}조" + (f"의{branch}" if branch else "")

        entry = corpus.get(key)
        if entry is None:
            failures.append((rid, ref, f"코퍼스에 '{key}' 없음"))
            continue

        cited_title = (m["title"] or "").strip()
        actual_title = entry["title"]
        if cited_title and cited_title not in actual_title:
            warnings.append((rid, ref, f"실제 제목: {actual_title}"))
        else:
            ok += 1

    print(f"검증 대상 {len(rules)}개 규칙 / 코퍼스 조문 {len(corpus)}건\n")
    if failures:
        print(f"[FAIL] 실재하지 않는 조문 인용 {len(failures)}건")
        for rid, ref, why in failures:
            print(f"  {rid}: {ref}\n     -> {why}")
        print()
    if warnings:
        print(f"[WARN] 조문은 있으나 제목 불일치 {len(warnings)}건")
        for rid, ref, why in warnings:
            print(f"  {rid}: {ref}\n     -> {why}")
        print()
    print(f"[OK] 조문·제목 모두 일치: {ok}건")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
