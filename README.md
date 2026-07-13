# Safety AI Control

현장 안전 AI 관제 시스템 Spring Boot 프로젝트 초안입니다.

## 구성

- Java 21
- Spring Boot 3.3.5
- Spring Web
- Spring Data JPA
- MySQL Connector/J
- Flyway
- React/Vite frontend mockup

## DB 스키마

- 설계 설명: `db_design.md`
- 원본 SQL: `schema.sql`
- Spring Boot 마이그레이션 SQL: `src/main/resources/db/migration/V1__init_schema.sql`

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
$env:DB_URL="jdbc:mysql://localhost:3306/safety_smartyard_control?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC"
$env:DB_USERNAME="admin123"
$env:DB_PASSWORD="admin123"
```

Gradle Wrapper를 추가하거나 IntelliJ에서 Gradle 프로젝트로 열어 실행하면 됩니다.

```powershell
./gradlew bootRun
```

## 확인 API

```text
GET /api/health
```
