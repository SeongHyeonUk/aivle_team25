# CLAUDE.md

작업허가서(PTW) 승인 지원 모듈 — AI 기반 스마트 조선소 안전 관리 시스템 기능 ②.
신규 허가서를 검토해 관리자에게 **판정 제안 + 근거**를 제시한다. 최종 승인은 항상 사람이 한다.

명세: `../../../작업 허가서/permit-approval-support.md` (저장소 루트의 `작업 허가서/`)
상세 문서는 [README.md](README.md) 하나로 통합되어 있다 (설치·검증 현황·함정·남은 일 포함).

## 절대 깨면 안 되는 것

이 모듈의 존재 이유가 걸린 제약이다. 명세 §2·§11이고, 코드가 이미 이렇게 되어 있다.

1. **판정은 룰엔진만 한다.** `verdict`를 결정하는 코드는 `rule_engine/orchestrator.py`의
   `summarize_verdict()` 하나뿐이고 순수 함수다. `engine.py`는 위반 목록만 반환한다.
   판정 로직을 다른 곳에 만들거나 LLM에게 맡기지 말 것.
2. **자동 승인 금지.** `PermitDecision.human_decision_required`는 `Literal[True]`,
   `verdict_source`는 `Literal["rule_engine"]`이다. 이걸 `bool`이나 `str`로 완화하면
   그 순간 자동 승인 경로가 열린다. `tests/test_orchestrator.py`가 지킨다.
3. **LLM은 설명만 쓴다.** `generator/rag.py`의 `model_copy(update=...)`에 들어가는 키는
   `reject_comment` · `recommended_actions` · `similar_cases` 셋뿐이다.
   `verdict`나 `violations`를 update dict에 넣는 코드가 생기면 경계가 무너진다.
4. **의존 방향은 단방향.** `generator/ → rule_engine/ · retrieval/ · schemas/`.
   `rule_engine`이 `generator`를 import하면 안 된다.
5. **학습하지 않는다.** 임베딩은 사전학습 모델 추론, 생성은 API 호출이다.
   `.fit()`, 옵티마이저, 체크포인트 저장이 등장하면 명세 위반이다.
6. **하드코딩 금지.** 규칙은 `rule_engine/rules/*.yaml`, 경로·모델명·top-k는 `config.yaml`.
7. **실제 조선소 허가서 양식·데이터 사용 금지.** KOSHA P-94 / OSHA 1915 공개 표준만 쓴다.

## 명령

```bash
python -m pytest -q                       # 114 passed
python -m tools.verify_legal_refs         # 룰 조문번호 ↔ 실제 법령 대조 (14건)
python -m tools.try_permit --list         # P-94 기반 샘플 허가서 목록
python -m tools.try_permit --all --no-retrieval   # 판정만 즉시 실행
python -m generator.rag --sample 3        # RAG 전체 경로 스모크 (API 키 필요)
python -m data_gen.generate_permits --count 500
python -m retrieval.index_builder all
```

`python -m retrieval.index_builder all --force`는 **CPU에서 58분**이 든다.
모델이나 청킹을 정말 바꿨을 때만 쓸 것. 그 외에는 벡터 캐시가 몇 초 만에 끝낸다.

## 환경 함정 (Windows + Anaconda)

- **`numpy`를 `torch`보다 먼저 import해야 한다.** 아니면 `OMP: Error #15`로 프로세스가 즉사한다.
  `retrieval/__init__.py`의 `import numpy`가 이를 강제한다 — 미사용처럼 보여도 **지우지 말 것.**
  `KMP_DUPLICATE_LIB_OK=TRUE` 우회는 "silently produce incorrect results" 경고 때문에 안 쓴다.
- **FAISS의 `read_index()`/`write_index()`는 한글 경로에서 실패한다** (경로에 `빅프`가 있다).
  `serialize_index`/`deserialize_index` + 파이썬 파일 IO를 쓴다 (`retrieval/index_builder.py`).
- **콘솔 한글이 깨지면** 실행 전에:
  `$env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8`
- **torch 스레드를 강제로 올리면 느려진다** (16코어 강제 시 3.65 → 1.92건/초). 기본값 유지.

## LLM (Gemini) 함정

- **Gemini 3.x는 thinking 모델이라 `max_output_tokens`를 사고 토큰과 나눠 쓴다.**
  1024로 두면 본문 JSON이 잘린 채 `finishReason=MAX_TOKENS`로 온다.
  현재 `max_output_tokens: 4096` + `thinking_level: low`.
- **모델명은 별칭이 아니라 버전으로 고정한다.** 설명문은 감사 대상이라 같은 허가서에
  어느 날 다른 설명이 나오면 안 된다. `gemini-2.5-flash`는 신규 키에 404를 낸다.
- **LLM 실패는 판정 실패가 아니다.** 키 부재·타임아웃·JSON 파손·429 어느 쪽이든
  예외를 밖으로 던지지 말고 설명이 빈 원본 판정을 그대로 반환한다.

## 규칙 추가·수정

`rule_engine/rules/`의 YAML만 고치면 된다. 엔진 코드 수정은 필요 없다.

- `hard_constraints.yaml` — 허가서 1건만 보고 판정 (HARD-*, COND-*)
- `simops.yaml` — 진행 중 허가서와 대조하는 동시작업 충돌 (SIMOPS-*)

작성 가능한 `condition` 키는 각 파일 상단 주석에 있다. 오타난 `work_type`이나
중복 `rule_id`는 **로드 시점에 예외로 터진다** — 조용히 꺼진 안전 규칙이 가장 위험하다.

규칙을 추가하면 반드시:
1. `python -m tools.verify_legal_refs`로 조문 실재 확인 (없는 조문 인용 = 감사 방어 불가)
2. 새 입력 필드가 필요하면 `schemas/permit.py`에 추가하고 `data_gen/generate_permits.py`의
   `_safe_permit()`에 **안전한 기본값**을 명시 — 아니면 정상 케이스에서 오탐이 난다
3. `python -m pytest -q`로 재현율·오탐 회귀 확인

## 파일 지도

```
schemas/permit.py            입출력 계약. 자동 승인을 타입으로 차단
rule_engine/
  orchestrator.py            verdict 종합 — 유일한 판정 지점
  engine.py                  규칙 평가 → 위반 목록만 반환
  conflict_matrix.py         블록 인접 판정 (현재 6열 격자 데모 가정)
  rules/*.yaml               규칙 14개
retrieval/
  searcher.py                PermitRetriever.retrieve() — 룰 근거 조문 결정론적 주입
  index_builder.py           FAISS 인덱스 구축 + 벡터 캐시
generator/
  llm_client.py              Gemini REST + 테스트용 MockClient
  prompts.py                 확정 verdict 주입, 허가서 본문은 데이터로 격리
  rag.py                     explain() = decide → retrieve → generate + 인용 후처리
tools/try_permit.py          P-94 양식 기반 샘플 실행기
samples/permits/*.json       손수 작성 허가서 10건 (의도가 note에 있다)
docs/*.xlsx                  데이터 정의서 · 모델 정의서
```

## 상태

명세 §9의 1~5단계 완료. 6단계 FastAPI는 백엔드 담당이라 이 모듈에서 만들지 않는다.
남은 `TODO(팀확인)` 15건은 코드 결함이 아니라 도메인 확인 대기 항목이다
(실제 야드 배치도, `work_type` enum 확정, 일부 조문의 적절성 등).
