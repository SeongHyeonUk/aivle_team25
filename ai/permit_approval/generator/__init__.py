"""RAG 생성기 패키지 — 명세 §6.3.

이 패키지는 **판정하지 않는다.** 룰엔진이 이미 확정한 verdict를 받아
그에 대한 자연어 설명(reject_comment)과 권고 조치(recommended_actions)만 만든다.

의존 방향은 단방향이다:

    generator/ -> rule_engine/, retrieval/, schemas/

역방향 import(rule_engine이 generator를 부르는 것)는 금지다. 그 순간
"LLM이 판정에 관여할 수 없다"는 구조적 보장이 사라진다.
"""
