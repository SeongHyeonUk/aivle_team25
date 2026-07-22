# 작업허가서 승인 지원 모듈 (PTW Approval Support)

AI 기반 스마트 조선소 안전 관리 시스템 / **기능 ② 작업허가서 승인 지원**

작업허가서(PTW) 승인 전 단계에서 신청 작업을 검토해 관리자에게 **판정 제안 + 근거**를 제시한다.
최종 승인은 항상 사람이 한다.

- 개발 명세: `작업 허가서/permit-approval-support.md` (저장소 루트)
- AI 에이전트용 요약: [CLAUDE.md](CLAUDE.md)
- 산출물 정의서: [docs/](docs/) (데이터 정의서 · 모델 정의서)

---

## 1. 현재 상태

명세 §9의 **1~5단계 완료**. 판정 + 근거 설명까지 나온다.

| 단계 | 상태 | 산출물 |
|---|---|---|
| 1. 입출력 스키마 | 완료 | `schemas/permit.py` — 다른 모든 작업의 계약 |
| 2. 합성 허가서 | 완료 | `data_gen/` — 500건 + 정답 라벨. 텍스트 필드는 템플릿 |
| 3. 룰엔진 판정 | 완료 | `rule_engine/` — 규칙 14개. **여기까지로 판정은 동작** |
| 4. 코퍼스·검색 | 완료 | `retrieval/` — 법령 875 조문 + 사례 1,818건, bge-m3 + FAISS |
| 5. RAG 생성기 | 완료 | `generator/` — Gemini 설명 생성 + 인용 무결성 후처리 |
| 6. FastAPI | **미착수** | 담당 미확정 (§11 참고) |

```bash
python -m pytest -q                # 114 passed
python -m tools.verify_legal_refs  # 14개 규칙 전부 조문·제목 일치
```

> LLM 키가 없거나 호출이 실패해도 **판정은 그대로 나온다.** 설명만 비는 것이
> 정상 동작이다 — 판정은 LLM 없이 이미 유효하다.

---

## 2. 빠른 시작

Python 3.11+ 필요.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.example .env     # 키 입력 (§3)
```

> torch를 CPU 인덱스에서 **먼저** 받는 이유: PyPI 기본 휠은 CUDA가 묶여 있어 2.5GB인데
> 이 모듈은 임베딩 추론만 하므로 GPU가 필요 없다. CPU판은 122MB다.
> `requirements.txt`만 돌리면 CUDA판이 깔린다.

```bash
python -m data_gen.generate_permits --count 500   # 합성 허가서
python -m retrieval.corpus_fetcher all            # 코퍼스 수집 (키 필요)
python -m retrieval.index_builder all             # 인덱스 구축
python -m pytest -q                               # 114 passed 나오면 완료
```

### 다른 PC로 옮길 때 — 먼저 읽을 것

**git만 받으면 안 된다.** 데이터가 전부 `.gitignore`에 걸려 있다.
빠진 것: `.env`(인증키) · `corpus/`(코퍼스·인덱스) · `data/synthetic/`(합성 허가서)

그냥 받아서 돌리면 **임베딩을 58분 다시 계산**해야 한다. 아래 13MB를 같이 옮기면 몇 초로 끝난다.

```
corpus/chunks/legal.jsonl          (0.9MB)
corpus/chunks/cases.jsonl          (1.4MB)
corpus/index/legal.vectors.npy     (3.5MB)   ← 21분짜리
corpus/index/legal.vector_ids.json
corpus/index/cases.vectors.npy     (7.4MB)   ← 37분짜리
corpus/index/cases.vector_ids.json
```

`.faiss` / `.meta.jsonl` / `.manifest.json`은 안 옮겨도 된다. 벡터만 있으면
`index_builder`가 몇 초 만에 다시 만든다.
`.env`는 옮기지 말고 새 PC에서 다시 만든다 — 키가 평문이라 USB에 담아 다닐 물건이 아니다.

인덱스 구축 시 `[legal] 전부 캐시에 있다 — 임베딩 생략`이 뜨면 성공이다.
진행률 막대가 돌면 캐시를 못 찾은 것이니 파일 위치를 확인할 것.
(bge-m3 모델 2.2GB는 새 PC에서 한 번 받아야 한다. `~/.cache/huggingface`)

> **함정**: 코퍼스·인덱스 파일만 옮기고 `torch`/`sentence-transformers`/`faiss-cpu`를
> 설치하지 않으면 `tests/test_retrieval.py` 10개가 **스킵되지 않고 실패한다**
> (`ModuleNotFoundError`). 스킵 조건이 "인덱스 파일 존재"라서, 파일은 있는데
> 라이브러리가 없는 조합을 통과시켜 버린다.

---

## 3. 인증키

| 변수 | 발급처 | 성격 |
|---|---|---|
| `LAW_OC` | [open.law.go.kr](https://open.law.go.kr/LSO/usr/usrOcInfoMod.do) | 본인이 지정하는 식별자. 비밀값 아님. 보통 이메일 @ 앞부분 |
| `DATA_GO_KR_SERVICE_KEY` | data.go.kr 마이페이지 | 64자 hex. **비밀값. 커밋 금지** |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) | 무료 티어. **비밀값. 커밋 금지** |

**인증키 발급은 사람이 직접 해야 한다** (회원가입·활용신청 절차):

1. [data.go.kr](https://www.data.go.kr) 가입 → 15121001, 15123696 활용신청
   (개발계정 자동승인) → 일반 인증키(Decoding) 확보
2. [open.law.go.kr](https://open.law.go.kr/LSO/openApi/cuAskList.do) → OPEN API 신청 → `OC` 값 확보
3. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → API 키 발급

공공데이터포털은 **계정당 키 하나**를 모든 API가 공유한다. 두 API에 각각 신청했어도 값은 같다.
`.env.example`은 git이 추적하므로 실제 키를 넣지 말 것. 실제 키는 `.env`에만.

키 없이 `corpus_fetcher`를 실행하면 무엇을 어디서 받아야 하는지 안내하고 종료한다.

---

## 4. 절대 건드리면 안 되는 것

명세 §2·§11의 핵심 제약이다. 코드 리뷰 시 여기부터 본다.

1. **판정은 룰엔진만 한다.** `verdict`를 결정하는 코드는 `rule_engine/orchestrator.py`의
   `summarize_verdict()` 하나뿐이고 순수 함수다. `engine.py`는 위반 목록만 반환한다.
2. **자동 승인은 타입으로 막혀 있다.** `PermitDecision.human_decision_required`는
   `Literal[True]`, `verdict_source`는 `Literal["rule_engine"]`. 관례가 아니라 타입이라
   다른 값을 가진 객체는 **생성 자체가 안 된다.** (`tests/test_orchestrator.py`가 검증)
3. **LLM이 붙어도 순서는 불변**: `verdict 확정 → LLM에 주입 → 설명만 생성`.
   `generator/rag.py`의 `model_copy(update=...)`에 들어가는 키는 `reject_comment` ·
   `recommended_actions` · `similar_cases` 셋뿐이다. `verdict`를 update dict에 넣는
   코드가 생기면 그 순간 경계가 무너진다.
4. **의존 방향은 단방향**: `generator/ → rule_engine/ · retrieval/ · schemas/`.
   역방향 import 금지.
5. **학습하지 않는다.** 임베딩은 사전학습 모델 추론, 생성은 API 호출이다.
6. **규칙은 YAML, 설정은 config.yaml.** 코드에 하드코딩하지 않는다.
7. **실제 조선소 허가서 양식·데이터 사용 금지.** KOSHA P-94 / OSHA 1915 공개 표준만.

---

## 5. 검증 현황

| 지표 | 결과 | 표본 |
|---|---|---|
| 룰엔진 재현율 (알려진 위반 포착) | 200/200 **100%** | 합성 500건 |
| 정상 케이스 오탐 | **0/300** | normal 시나리오 |
| 판정 정답 일치율 | 500/500 **100%** | 합성 500건 |
| 인덱스 자기검색 정확도 | 875/875 | 법령 조문 |
| 근거 조문 포함률 — 의미 검색 단독 | 17/60 **28.3%** | 위반 보유 허가서 60건 |
| 근거 조문 포함률 — 룰 주입 후 | 60/60 **100%** | 위반 보유 허가서 60건 |
| 인용 무결성 (환각 인용) | **0/11** | 실호출 7건 |

생성기는 인젝션(허가서 본문 + LLM 응답 양쪽)·인용 환각·JSON 파손·호출 실패
전 시나리오에서 verdict 불변을 확인했다. `tests/test_generator.py`는 MockClient
기반이라 API 키·네트워크 없이 항상 돈다.

상세 수치는 [docs/모델 정의서](docs/) 참고.

---

## 6. 직접 시험해보기

KOSHA **P-94-2019 안전작업허가지침** 양식 기반 샘플 10건이 들어 있다.

```bash
python -m tools.try_permit --list                  # 목록 + 각 케이스 의도
python -m tools.try_permit --all --no-retrieval    # 전부, 판정만 (즉시)
python -m tools.try_permit fire-watch              # 검색·LLM 설명까지 전체 경로
python -m tools.try_permit --file 내허가서.json     # 직접 만든 파일
python -m generator.rag --sample 3                 # 합성 데이터로 스모크
```

`--no-retrieval`은 임베딩 모델을 안 띄워 즉시 실행되고, `--no-llm`은 API 쿼터를
아낀다. 판정 자체는 LLM과 무관하므로 결과가 같다.

각 샘플의 `note`에 **어디를 바꾸면 판정이 뒤집히는지** 적어두었다.
P-94 양식과 스키마의 대응표는 [samples/README.md](samples/README.md) 참고.

---

## 7. 규칙 추가·수정

`rule_engine/rules/`의 YAML만 고치면 된다. 엔진 코드 수정은 필요 없다.

- `hard_constraints.yaml` — 허가서 1건만 보고 판정 (HARD-*, COND-*)
- `simops.yaml` — 진행 중 허가서와 대조하는 동시작업 충돌 (SIMOPS-*)

작성 가능한 `condition` 키는 각 파일 상단 주석에 있다. 오타난 `work_type`이나
중복 `rule_id`는 **로드 시점에 예외로 터진다** — 조용히 꺼진 안전 규칙이
가장 위험한 실패 모드이기 때문이다.

규칙을 추가하면 반드시:

1. `python -m tools.verify_legal_refs` — 조문 실재 확인.
   존재하지 않는 조문을 인용하면 종료코드 1로 실패한다. 근거 없는 반려는
   감사에서 방어할 수 없다.
2. 새 입력 필드가 필요하면 `schemas/permit.py`에 추가하고
   `data_gen/generate_permits.py`의 `_safe_permit()`에 **안전한 기본값을 명시**한다.
   빠뜨리면 정상 케이스에서 오탐이 난다.
3. `python -m pytest -q` — 재현율·오탐 회귀 확인.

---

## 8. 데이터

### 합성 허가서 (`data/synthetic/`)

실제 조선소 허가서는 기밀이라 사용할 수 없다(명세 §11). KOSHA P-94 / OSHA 1915
공개 표준 구조로 생성한다. seed 고정이라 재현 가능하므로 커밋하지 않는다.

`permits.jsonl` — 한 줄이 평가 케이스 1건:

```json
{"case_id": "CASE-00000", "permit": {...}, "active_permits": [{...}]}
```

`labels.jsonl` — 그 케이스의 정답지:

```json
{"case_id": "CASE-00000", "scenario": "simops_conflict",
 "expected_violations": ["SIMOPS-004"], "expected_verdict": "반려",
 "risk_categories": ["화재폭발"]}
```

> ### ⚠ 라벨 누수 경고 (명세 §8)
> `labels.jsonl`은 **룰엔진 테스트용 정답지**다. XGBoost 등 다른 모듈이 이 값을
> 위험도 학습 라벨로 그대로 복사하면 모델은 룰엔진을 복제할 뿐 아무것도 학습하지
> 못한다. 학습 라벨은 룰 점수를 확률로 삼아 사고 발생을 확률적으로 샘플링하고,
> 룰에 없는 상호작용 변수를 심어 별도로 생성해야 한다.
> `TODO(팀확인)`: XGBoost 모듈과 인터페이스 협의 필요.

### 코퍼스 (`corpus/`)

명세 §7의 소스는 **전부 공식 무료 API로 제공된다. 크롤링하지 않는다.**

| 코퍼스 | 출처 | 라이선스 |
|---|---|---|
| 산업안전보건기준에 관한 규칙 | [국가법령정보 공동활용 OPEN API](https://open.law.go.kr/LSO/openApi/guideResult.do) | 공공저작물, 무료 |
| KOSHA GUIDE·안전보건법령 | [공공데이터포털 15123696](https://www.data.go.kr/data/15123696/openapi.do) | 이용허락범위 제한 없음 |
| 국내 재해사례 | [공공데이터포털 15121001](https://www.data.go.kr/data/15121001/openapi.do) | 이용허락범위 제한 없음 |

**2026-07-22 수집 완료:**

| 파일 | 건수 | 내용 |
|---|---|---|
| `corpus/chunks/legal.jsonl` | 875 | 산업안전보건기준에 관한 규칙 690 + 산업안전보건법 185 (조문 단위) |
| `corpus/chunks/cases.jsonl` | 1,818 | 조선업 378 + 제조업 1,440 (사례 단위) |

재해사례 전체는 6,348건(건설업 4,185 / 제조업 1,440 / 조선업 378 / 서비스업 345)이지만,
`config.yaml`의 `keep_businesses`로 조선소 작업과 직결되는 두 업종만 남겨
CPU 임베딩 시간을 5시간에서 37분으로 줄였다.

---

## 9. 검색 (Retrieval)

명세 §6.2에 따라 **법령과 사고사례를 분리 인덱싱**한다. 한 인덱스에 섞으면
사례가 법령 자리를 차지해서, 근거 조문을 요구하는 자리에 사고 이야기가 올라온다.

```
corpus/index/
├── legal.faiss + legal.meta.jsonl + legal.manifest.json    (875)
└── cases.faiss + cases.meta.jsonl + cases.manifest.json  (1,818)
```

- **모델**: `BAAI/bge-m3` (1,024차원). 학습하지 않고 추론만 한다.
- **인덱스**: `IndexFlatIP` 완전탐색. 청크가 1만 건 이하라 근사 인덱스(IVF/HNSW)는
  재현성만 떨어뜨린다. 벡터를 정규화해 내적 = 코사인 유사도.
- **manifest**: 어떤 모델·차원·건수로 만들었는지 기록한다. 검색 시 현재 모델과
  대조해 불일치면 거부한다 — 다른 모델로 만든 인덱스를 검색하면 **에러 없이
  무의미한 결과**가 나오기 때문이다.
- **쿼리 조립**: `build_query()`가 `work_type + area_type + work_description +
  위반 요약`을 합친다. 위반 요약이 핵심이다. 허가서 본문만 넣으면 "용접 작업"
  수준의 일반 문서가 걸리는데, "인접 인화물이 있는데 환기가 없다"가 들어가면
  그 상황에 맞는 조문이 올라온다.
- **룰 근거 조문 주입**: `PermitRetriever.retrieve()`는 의미 검색 결과에 더해,
  룰엔진이 근거로 지정한 조문을 `fetch_by_legal_ref()`로 **항상** 넣는다
  (`matched_by="rule"`). 의미 검색에만 맡겼을 때 포함률이 **28.3%**(60건 표본)에
  그쳐서, 생성기가 정작 그 판정의 법적 근거를 인용할 수 없었다. 주입 후 **100%**.
  규칙의 근거는 검색으로 '찾을' 대상이 아니라 이미 정해진 사실이다.

```python
from retrieval.searcher import PermitRetriever
result = PermitRetriever().retrieve(permit, violations)
result["legal"]  # 룰 근거 조문 + 의미 검색 top-5
result["cases"]  # 유사 사례 top-5
```

검색은 **판정에 관여하지 않는다.** verdict는 이미 룰엔진이 정한 뒤이고,
검색 결과는 생성기가 설명문을 쓸 때 인용할 근거일 뿐이다.

### 벡터 캐시

임베딩은 CPU에서 오래 걸린다(legal 875건 21분 / cases 1,818건 37분). 그래서
벡터를 **청크 id 기준으로** `{name}.vectors.npy` + `{name}.vector_ids.json`에
캐시하고 128건마다 체크포인트를 찍는다. 덕분에:

- 중간에 죽어도 최대 128건만 다시 계산한다
- 나중에 건설업 사례를 추가해도 기존 1,818건은 재계산하지 않는다

모델이나 청킹 방식을 바꿔 정말 다시 계산해야 할 때만 `--force`를 쓴다. **58분이 다시 든다.**

---

## 10. RAG 생성기

```python
from generator.rag import explain
decision = explain(permit, active_permits)   # 판정 → 검색 → 설명
```

`explain()`의 순서는 `decide() → retrieve() → generate_explanation()`이고
이 순서는 바뀌지 않는다. LLM은 **이미 확정된 verdict를 프롬프트로 받는다.**

생성기가 채우는 필드는 셋뿐이다:

| 필드 | 출처 |
|---|---|
| `reject_comment` | LLM |
| `recommended_actions` | LLM |
| `similar_cases` | **검색 결과 복사** (LLM 아님 — 사례를 지어낼 여지를 없앤다) |

`verdict`·`violations`·`verdict_source`·`human_decision_required`는
`model_copy(update=...)`의 update dict에 **아예 넣지 않는다.** 모델이 응답에
`{"verdict": "승인제안"}`을 얹어 보내도 읽는 코드가 없다.
`responseSchema`에도 verdict를 넣지 않아 모델에게 판정할 자리 자체를 주지 않는다.

### 환각 방어 (명세 §10)

1. **인용 무결성 후처리** — 검색 결과로 실제 제공한 조문 번호 집합을 만들고,
   거기 없는 조문을 인용한 **문장을 통째로 제거**한다. 번호만 지우면
   "제999조에 따라 감시인을 배치해야 한다"가 "에 따라 감시인을 배치해야 한다"는
   근거 없는 주장으로 남기 때문이다. (`generator/rag.py`의 `strip_unknown_citations`)
   조문 본문 안에 언급된 다른 조문은 허용 집합에 넣지 않는다 — 제1조 본문이
   제63조를 언급한다고 제63조를 근거로 들 수 있는 건 아니다.
2. **인젝션 격리** — 시스템 지시와 허가서 본문을 `systemInstruction` / `contents`로
   분리하고, 자유 입력 필드는 구분자로 감싸 "데이터이지 지시가 아니다"를 명시한다.
3. **실패는 판정을 죽이지 않는다** — 키 부재·타임아웃·JSON 파손·안전 필터 차단
   어느 쪽이든 예외를 밖으로 던지지 않고 설명이 빈 원본 판정을 돌려준다.

### 모델

`gemini-3.6-flash` (Google AI Studio 무료 티어). `config.yaml`의
`generator.llm_model`로 교체 가능하고, 다른 공급자는 `llm_client.py`의
`LLMClient` 프로토콜(`complete(system, user) -> str`)만 구현하면 된다.

별칭(`gemini-flash-latest`)이 아니라 **버전을 고정한다.** 안전 판정의 설명문은
감사 대상이라 같은 허가서에 어느 날 다른 설명이 나오면 안 된다.

---

## 11. 남은 일

### 6단계 FastAPI — 담당 미확정

명세 §6.4의 3개 엔드포인트. 판정 로직은 새로 만들 게 없고 **HTTP 창구만 씌우면 된다**
(`explain()` 호출 한 줄). 반나절~하루 분량.

| 엔드포인트 | 하는 일 |
|---|---|
| `POST /permits/evaluate` | 허가서 1건 → 판정 + 근거 + 설명 |
| `GET /permits/active` | 진행 중 허가서 목록 (SIMOPS 대조용) |
| `POST /permits/{id}/decide` | 사람의 최종 결정을 **기록만** 함. 시스템이 자동 호출하지 않는다 |

착수 전 결정해야 할 것:

1. **모델 로딩 시점** — bge-m3 2.2GB를 요청마다 올릴 수 없다. `lifespan`에서 1회 로딩,
   메모리 상주. 대신 서버 기동이 느리니 헬스체크 유예를 넉넉히 줘야 한다.
2. **진행 중 허가서를 누가 가져오나** ← 가장 중요
   - (A) Spring이 목록을 요청 body에 실어 보낸다 → AI 서버가 DB를 몰라도 된다. **권장**
   - (B) AI 서버가 직접 DB 조회 → 접속정보·커넥션풀·스키마 변경을 떠안는다
3. **응답 지연** — 룰엔진 1ms 미만 / 검색 0.31초 / **LLM 5~7초**.
   신청자를 7초 기다리게 할지, 판정만 즉시 주고 설명은 나중에 채울지.
   데모 목적이면 전자로 충분하다.

> 이 작업은 Python 코드다. Spring 담당자가 하기 애매하므로 팀에서 담당을 확정할 것.

### 배포 (AWS)

현재 상태로는 **배포 불가.** 블로커:

| 블로커 | 내용 |
|---|---|
| HTTP 진입점 | 위 FastAPI가 있어야 Spring이 호출할 수 있다 |
| 모델 크기 | bge-m3 2.2GB + torch. **Lambda 불가**(압축 250MB 제한) → ECS Fargate / EC2, 메모리 4GB 이상 |
| 인덱스 전달 | 13MB 벡터가 gitignore. 이미지 빌드 때 재생성하면 58분 → S3에서 받거나 이미지에 굽기 |
| 재현성 | `requirements.txt`가 전부 `>=` 범위. torch CPU 인덱스 URL이 주석이라 그대로 설치하면 CUDA판이 깔린다 |
| DB 스키마 | `permit_analysis_results`에 `verdict` 컬럼이 없다 (아래) |

### Spring 백엔드 연동

백엔드에 결과 수신구는 이미 열려 있다:
`POST /api/ai/work-permits/{permitId}/analysis-results` (`AiModelController`).

다만 스키마 간극이 있다. 상세는 [docs/데이터 정의서](docs/)의 `DB 매핑(요청안)` 시트 참고.

- **`work_permits`에 안전조치 컬럼 6개가 없다** — `supervisor_present`,
  `gas_measured`, `ventilation`, `adjacent_flammable`, `fire_watch_assigned`,
  `declared_ppe`. 우리 규칙 14개 중 9개가 이 값을 쓴다. 안 오면 기본값(미조치)으로
  판정하므로 **정상 작업도 위반으로 잡힌다.**
- **`permit_analysis_results`에 `verdict`·`verdict_source`·`human_decision_required`가
  없다.** 이 모듈의 핵심 출력을 담을 자리가 없다. JSON에 밀어 넣으면 동작은 하지만
  "판정 주체는 룰엔진, 자동 승인 없음" 보장이 DB 레벨에서 사라진다.
- **`confidence` 컬럼은 비워야 한다.** 우리 판정은 확률이 아니라 결정론적 라벨이다.
  임의 수치를 넣으면 "AI가 확신도 87%로 반려"처럼 오해를 부른다.
- **`blocks.grid_x / grid_y`가 이미 있다** — 야드 배치도 TODO를 풀 수 있다.
  `conflict_matrix.py`의 `AdjacencyResolver` 구현체만 교체하면 `engine.py`는
  손대지 않고 실제 배치도 기반 판정으로 바뀐다.

프런트 `Permits.jsx`는 아직 전부 하드코딩 목업이다.

### 미확정 사항 (`TODO(팀확인)`, 15건)

코드 결함이 아니라 도메인 확인 대기 항목이다.

| 항목 | 위치 | 내용 |
|---|---|---|
| 실제 야드 배치도 | `rule_engine/conflict_matrix.py` | 현재 `B-12`를 6열 격자로 펼친 데모 가정. `blocks` 테이블로 대체 가능 |
| `work_type` enum | `schemas/permit.py` | 조선소 현장 용어 기준 누락 항목 확인 |
| 조문 적절성 | YAML 주석 | 조문 실재는 전부 검증됨. COND-003(양중↔제39조), SIMOPS-003(도장·사상↔제422조)이 해당 상황의 근거로 맞는지 도메인 판단 필요 |
| LLM 모델 등급 | `config.yaml` | `gemini-3.6-flash`로 확정. 품질 부족 시 pro 계열(무료 한도 감소) |
| 건설업 사례 추가 | `config.yaml` `keep_businesses` | 추락·낙하 등 조선소와 겹치는 재해가 많다. 추가해도 기존 1,818건은 재계산 안 함 |
| 위험도 라벨 생성 | `data_gen/` | XGBoost 모듈과 협의. `labels.jsonl`을 학습 라벨로 쓰면 안 됨 |
| P-94 미대응 항목 | `samples/README.md` | 가스농도 수치 판정, 고소·정전·굴착·방사선 보충작업 규칙 없음 |

---

## 12. 함정 모음 (다시 밟지 말 것)

### 환경 (Windows + Anaconda)

- **`torch`를 `numpy`보다 먼저 import하면 프로세스가 즉사한다** (`OMP: Error #15`).
  `retrieval/__init__.py`의 `import numpy`가 이를 막는다. **그 줄을 지우지 말 것.**
  `KMP_DUPLICATE_LIB_OK=TRUE` 우회는 "silently produce incorrect results" 경고가
  붙어 있어 채택하지 않았다.
- **FAISS의 `write_index()`/`read_index()`는 한글 경로에서 실패할 수 있다**
  (경로에 `빅프`가 있다). `serialize_index`/`deserialize_index` + 파이썬 파일 IO를 쓴다.
  `retrieval/index_builder.py`의 `write_faiss_index()` 참고.
- **`np.save()`는 파일명이 `.npy`로 안 끝나면 확장자를 덧붙인다.** 임시 파일을 만들 때
  이것 때문에 뒤따르는 `replace()`가 없는 파일을 가리켜 죽었다. 파일 객체를 넘기면 안 그런다.
- **torch 스레드를 강제로 올리면 오히려 느려진다** (16코어 강제 시 3.65 → 1.92건/초).
  기본값을 건드리지 말 것.
- **콘솔 한글이 깨지면** 실행 전에:
  `$env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8`

### 데이터 수집

- **재해사례 API의 `callApiId` 고정값은 `1060`.** 포털 설명문의 "국내재해사례 게시판
  조회"는 값이 아니라 파라미터의 의미 설명이다. Swagger 스펙의 `paramtrBassValue`에서 찾았다.
- **재해사례 API는 `business`·`keyword` 파라미터를 무시한다.** 조선업으로 요청해도
  건설업이 섞여 온다. 업종 필터는 응답의 `business` 필드로 클라이언트에서 건다.
- **법령 API 응답에 편·장·절 제목 행이 섞여 있고, 그게 다음 조문의 번호를 달고 온다.**
  `조문여부 == "조문"`으로 걸러야 한다. 안 그러면 1,065행 중 190행이 중복 id가 된다.

### LLM (Gemini)

- **`gemini-2.5-flash`는 신규 키에 404를 낸다** ("no longer available to new users").
  실호출로 확인한 결과 `3.5-flash`는 503(과부하), `2.0-flash`는 429(무료 쿼터),
  **`gemini-3.6-flash`가 200**이었다. 모델이 안 뜨면 먼저 ListModels로 확인할 것:
  `GET https://generativelanguage.googleapis.com/v1beta/models`
- **Gemini 3.x는 thinking 모델이라 `maxOutputTokens`를 사고 토큰과 나눠 쓴다.**
  1024로 두면 본문 JSON이 중간에 잘려 `finishReason=MAX_TOKENS`로 오고, 파싱 단계에서
  "JSON을 찾지 못했다"는 엉뚱한 메시지만 남는다(실측 실패 3/3).
  `max_output_tokens: 4096` + `thinking_level: low`로 해결했다.
  `llm_client._extract_text()`가 MAX_TOKENS를 별도 메시지로 구분한다.
- **무료 티어 쿼터로 429가 난다.** 연속 10건 호출 시 3건 실패했다. 전부 설계대로
  "설명 없는 판정"으로 폴백했다.

### 설계

- **룰의 근거 조문은 의미 검색에 맡기면 안 된다.** 검색 top-5에 들어오는 비율이
  28.3%(60건 표본)였다. `PermitRetriever`가 결정론적으로 주입하도록 고쳐 100%가 됐다.
- **임베딩은 반드시 캐시하고 체크포인트를 찍는다.** CPU에서 58분짜리 작업이라
  마지막 단계에서 죽으면 통째로 날아간다. 실제로 두 번 겪었다.
- **새 입력 필드를 추가하면 `_safe_permit()`에 안전한 기본값을 넣어야 한다.**
  COND-005 작업 때 이걸 빠뜨리면 정상 케이스 300건이 전부 오탐이 될 뻔했다.

---

## 13. 구조

```
permit_approval/
├── CLAUDE.md                # AI 에이전트용 요약 (제약·명령·함정)
├── config.yaml              # 경로·모델명·top-k·시나리오 비율. 하드코딩 금지 대상
├── config_loader.py
├── schemas/permit.py        # 입출력 계약. 자동 승인을 타입으로 차단
├── rule_engine/
│   ├── engine.py            # 규칙 평가 → 위반 목록만 반환
│   ├── orchestrator.py      # verdict 종합 — 유일한 판정 지점
│   ├── conflict_matrix.py   # 블록 인접 판정 (현재 6열 격자 데모 가정)
│   └── rules/*.yaml         # 규칙 14개 — 코드 수정 없이 편집 가능
├── data_gen/                # 합성 허가서 + 정답 라벨
├── retrieval/
│   ├── corpus_fetcher.py    # 공식 API 수집·청킹
│   ├── embedder.py          # bge-m3 래퍼
│   ├── index_builder.py     # FAISS 인덱스 + 벡터 캐시
│   └── searcher.py          # top-k 검색 + 룰 근거 조문 주입
├── generator/
│   ├── llm_client.py        # Gemini REST + 테스트용 MockClient
│   ├── prompts.py           # 시스템 지시 + 프롬프트 조립
│   └── rag.py               # explain() 파이프라인 + 인용 무결성 후처리
├── samples/permits/         # P-94 양식 기반 손수 작성 허가서 10건
├── tools/
│   ├── verify_legal_refs.py # 룰 조문번호 ↔ 실제 법령 교차 검증
│   └── try_permit.py        # 샘플·직접 작성 허가서 실행기
├── docs/                    # 데이터 정의서 · 모델 정의서 (xlsx)
└── tests/                   # 114개
```
