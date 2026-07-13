# SQL 교차검증 결과

## 검증 기준

- 요구사항 정의서의 기능이 테이블로 매핑되는지 확인
- 기존 ERD의 주요 엔티티가 빠지지 않았는지 확인
- FK 참조 대상 테이블이 생성 순서상 먼저 존재하는지 확인
- 인덱스가 실제 존재하는 테이블/컬럼을 참조하는지 확인
- PostgreSQL에서 문제가 될 수 있는 제약조건을 확인

## 구조 검증 결과

- `CREATE TABLE`: 31개
- `CREATE INDEX`: 9개
- FK 참조 대상 테이블/컬럼: 이상 없음
- FK 생성 순서: 이상 없음
- 인덱스 대상 테이블/컬럼: 이상 없음
- 로컬 `psql` 실행 검증: `psql` 명령이 설치되어 있지 않아 미실행

## 반영한 수정

- `user_roles`의 `site_id`는 전역 권한일 때 `NULL`이 될 수 있으므로 복합 PK에서 제외했습니다.
- 대신 `user_roles.id`를 PK로 두고, `site_id IS NULL` / `site_id IS NOT NULL` 기준 partial unique index를 분리했습니다.
- 기존 `CREATE EXTENSION IF NOT EXISTS pgcrypto;`는 현재 스키마에서 쓰는 함수가 없어 제거했습니다.
- 각 테이블 블록에 `[CORE]`, `[FULL]` 주석을 달았습니다.
- `[FULL]` 테이블에는 어떤 기능 때문에 필요한지 SQL 주석으로 설명을 붙였습니다.

## 요구사항 매핑 확인

| 요구사항 영역 | 대응 테이블 | 판정 |
|---|---|---|
| 계정/로그인 | `users`, `roles`, `user_roles`, `auth_sessions` | OK |
| 허가서 신청/문서 첨부 | `work_permits`, `files`, `work_permit_files` | OK |
| 허가서 AI 분석 | `permit_analysis_results`, `safety_rules`, `rule_checks` | OK |
| 유사 사고 검색 | `similar_accident_results` | OK |
| 승인 워크플로우 | `approval_flows`, `approval_steps` | OK |
| TBM 브리핑 | `tbm_sessions`, `tbm_materials`, `tbm_attendance` | OK |
| 체크리스트 | `checklist_templates`, `checklist_items`, `checklist_responses` | OK |
| 현장/블록/위험구역 | `sites`, `blocks`, `danger_zones` | OK |
| CCTV/ROI/PPE 감지 | `cameras`, `vision_detections` | OK |
| 신고/관제 이벤트 | `safety_events`, `event_actions` | OK |
| 위험도/What-if | `risk_scores`, `risk_simulations` | OK |
| 알림 | `notifications` | OK |
| 모델 운영 로그 | `model_runs` | OK |
| 감사 로그 | `audit_logs` | OK |

## 설계상 주의할 점

- MVP만 구현한다면 `[FULL]` 테이블은 일부 생략해도 됩니다.
- `JSONB` 컬럼은 모델 출력, ROI polygon, bbox, 이벤트 payload처럼 구조가 바뀔 수 있는 데이터에 사용했습니다.
- `model_runs.input_ref_id`는 여러 테이블을 참조할 수 있는 범용 ID라 FK를 걸지 않았습니다.
- `safety_events`는 사용자 신고와 AI 탐지 이벤트를 통합하는 테이블입니다.
- `risk_scores`는 허가서, 블록, 위험구역, 이벤트 중 하나 이상과 연결될 수 있게 FK를 nullable로 열어두었습니다.

## 최종 판정

현재 SQL은 요구사항 정의서와 기존 ERD 기준으로 구조상 큰 충돌은 없습니다.
발표/설계 단계에서는 `초기 DB 스키마 설계안`으로 사용해도 됩니다.
다만 실제 구현 시에는 MVP 범위에 맞춰 `[FULL]` 테이블을 줄이는 것이 좋습니다.
