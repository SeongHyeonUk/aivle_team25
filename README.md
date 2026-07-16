# Safety AI Control

현장 안전 AI 관제 시스템 Spring Boot 프로젝트 초안입니다.

## 구성

- Java 17
- Spring Boot 3.3.5
- Spring Web
- Spring Data JPA
- MySQL Connector/J
- Flyway
- React/Vite frontend mockup

## DB 스키마

- 설계 설명: `db_design.md`
- 원본 SQL: `schema.sql`
- Spring Boot 마이그레이션 SQL: `backend/src/main/resources/db/migration/`
- 역할 확장 마이그레이션: `V3__add_operational_roles.sql`

## 프론트 목업

- 원본 React/Vite 목업: `frontend/`

프론트는 현재 백엔드에 통합하지 않고 목업 소스로만 보관합니다.
화면을 확인하려면 `frontend` 폴더에서 의존성을 설치한 뒤 Vite 개발 서버를 실행합니다.

```powershell
cd frontend
npm install
npm run dev
```

## 실행 전 준비

MySQL 8 DB를 만들고 환경변수를 설정합니다. Docker가 설치된 로컬 환경에서는 `docker compose up -d mysql`로 실행할 수 있습니다.

```powershell
$env:DB_URL="jdbc:mysql://localhost:3307/safety_smartyard_control?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC"
$env:DB_USERNAME="admin123"
$env:DB_PASSWORD="admin123"
```

Gradle Wrapper를 추가하거나 IntelliJ에서 Gradle 프로젝트로 열어 실행하면 됩니다.

```powershell
.\gradlew.bat :backend:bootRun
```

## 확인 API

```text
GET /api/health
```

## 인증 및 역할

로그인 성공 시 반환되는 `accessToken`은 DB 세션 기반 Bearer 토큰입니다. 인증이 필요한 API에는 다음 헤더를 전달합니다.

```http
Authorization: Bearer {accessToken}
```

| 역할 | 용도 |
| --- | --- |
| `WORKER` | 게시판, 파일, 작업허가서, 본인 위험 신고 등 일반 작업자 기능 |
| `SAFETY_MANAGER` | 관제 대시보드, 전체 위험 이벤트, AI 분석 및 위험 점수 조회 |
| `ADMIN` | 모든 운영 조회와 기준정보·AI 결과·위험 점수 변경 |
| `AI_SERVICE` | AI 결과와 위험 점수를 등록하는 기계 계정 |

회원가입 계정에는 `WORKER` 역할이 자동 부여됩니다. `ADMIN`은 `BOOTSTRAP_ADMIN_*` 환경변수로 최초 생성할 수 있으며, `SAFETY_MANAGER`와 `AI_SERVICE`는 관리자가 DB에서 명시적으로 배정해야 합니다.

```sql
INSERT INTO user_roles (user_id, role_id, site_id)
SELECT :user_id, id, NULL
FROM roles
WHERE role_code = 'SAFETY_MANAGER';
```

역할 정의는 Flyway가 자동 등록하지만 사용자 배정은 자동으로 수행하지 않습니다.
