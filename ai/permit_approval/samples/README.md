# P-94 기반 조선소 작업허가서 샘플

KOSHA GUIDE **P-94-2019 안전작업허가지침**의 `<별지양식1> 화기작업 허가서` /
`<별지양식2> 일반위험작업 허가서`를 기준으로 만든 손수 작성 샘플이다.
합성 생성기(`data_gen/`)가 만드는 것과 달리 **사람이 읽고 고치라고** 만든 파일이라
시나리오 의도를 `note`에 적어 두었다.

```bash
python -m tools.try_permit --list             # 샘플 목록
python -m tools.try_permit hot-work-tank      # 1건 실행
python -m tools.try_permit --all --no-llm     # 전부, LLM 없이 (쿼터 절약)
python -m tools.try_permit --file 내파일.json  # 직접 만든 파일 실행
```

## P-94 양식 ↔ 시스템 스키마 대응

P-94는 **PSM(공정안전) 대상 화학공장** 기준 지침이라 조선소 야드 작업과 완전히
겹치지는 않는다. 아래는 우리 스키마가 실제로 받는 필드와의 대응이다.

| P-94 양식 항목 | 시스템 필드 | 비고 |
|---|---|---|
| 허가번호 | `permit_id` | |
| 작업허가기간 | `time_window.start` / `.end` | P-94 §4.6: 일일 정상근무시간 초과 불가 |
| 작업지역(장소) / 장치명 | `zone.block_id`, `zone.area_type` | 조선소는 블록·도크·탱크 |
| 작업 개요 | `work_description` | 신청자 자유 입력 |
| 화기작업 / 일반위험작업 구분 | `work_type` | 아래 매핑 참조 |
| 안전조치: 가스농도측정 | `special_conditions.gas_measured` | |
| 안전조치: 불활성가스 치환 및 환기 / 환기장비 | `special_conditions.ventilation` | |
| 안전조치: 작업주위 가연성물질 제거 | `special_conditions.adjacent_flammable` | 제거 못 했으면 `true` |
| 안전조치: 운전요원의 입회 | `supervisor_present` | 관리감독자·감시인 |
| 비산불티 차단막 + 화기작업 입회(P-94 6.1(3)아) | `special_conditions.fire_watch_assigned` | 제241조의2 화재감시자 |
| 안전장구 | `declared_ppe` | |
| 보충작업허가: 밀폐공간 | `work_type: 밀폐공간작업` | 우리는 별도 작업으로 모델링 |
| 보충작업허가: 중장비 | `work_type: 양중` | |
| 작업 인원 | `worker_count` | P-94 양식에는 없음. 우리 규칙(COND-004)이 사용 |

### work_type 매핑

| P-94 구분 | 우리 `work_type` |
|---|---|
| 화기작업 (용접·용단·연마·드릴) | `화기작업`, `용접` |
| 일반위험작업 | `일반`, `취부`, `사상`, `도장` |
| 보충작업 — 밀폐공간 출입 | `밀폐공간작업` |
| 보충작업 — 중장비 사용 | `양중` |

### 모델링하지 않는 P-94 항목

이 시스템은 **승인 전 위험 판정**만 한다. 아래는 결재·기록 영역이라 스키마에 없다.

- 발급자 / 승인자 / 입회자 / 관련부서 협조자 서명란 → 백엔드의 결재 기능
- 첨부서류 체크(작업계획서·소화기목록·특수작업절차서·도면)
- 가스농도 측정 **수치**(HC 0%, O₂ 18% 이상, CO 30ppm 미만, CO₂ 1.5% 미만, H₂S 10ppm 미만)
  → 현재는 측정 **여부**(`gas_measured`)만 본다
- 정전 / 굴착 / 방사선 / 고소 보충작업 → 대응 규칙 없음 (룰셋 확장 후보)
- 작업허가 연장, 작업완료·복원 상태

> 위 항목을 판정에 쓰려면 `schemas/permit.py`에 필드를 추가하고
> `rule_engine/rules/*.yaml`에 규칙을 넣으면 된다. 엔진 코드는 건드릴 필요가 없다.

## 파일 형식

```json
{
  "note": "이 케이스의 의도 (실행 결과에 표시된다)",
  "permit": { ... PermitRequest ... },
  "active_permits": [ { ... PermitRequest ... } ]
}
```

`active_permits`는 **지금 승인되어 진행 중인** 허가서 목록이다. SIMOPS(동시작업)
충돌 판정에만 쓰인다. 비워 두면 단일 허가서 규칙만 평가한다.
