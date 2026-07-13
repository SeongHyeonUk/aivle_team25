/*
  Project: 현장 안전 AI 관제 시스템
  Purpose: 요구사항 정의서 + ERD 기반 PostgreSQL 초기 스키마

  구분:
  - [CORE] MVP 구현에도 거의 필요한 핵심 테이블
  - [FULL] 요구사항 정의서 기능을 그대로 구현할 때 필요한 확장 테이블

  참고:
  - AI 출력 결과는 추후 모델 응답 포맷이 바뀔 수 있어 JSONB를 같이 둔다.
  - 파일은 files 테이블에 모으고, 업무 테이블에서 FK로 연결한다.
*/

-- =========================================================
-- [CORE] 사용자 / 권한
-- 기능: 로그인, 로그아웃, 사용자 정보, 관리자/작업자 권한 구분
-- 요구사항 매칭:
-- - 계정 > 로그인
-- - 계정 > 로그아웃
-- - 기준정보 > 권한 관리(RBAC)
-- =========================================================

CREATE TABLE sites (
  id BIGSERIAL PRIMARY KEY,
  site_code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  address TEXT,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  employee_no VARCHAR(50) UNIQUE,
  username VARCHAR(80) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name VARCHAR(80) NOT NULL,
  phone VARCHAR(30),
  company_name VARCHAR(150),
  language VARCHAR(20) DEFAULT 'ko',
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id BIGSERIAL PRIMARY KEY,
  role_code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(80) NOT NULL,
  description TEXT
);

CREATE TABLE user_roles (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  role_id BIGINT NOT NULL REFERENCES roles(id),
  site_id BIGINT REFERENCES sites(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_user_roles_site
  ON user_roles(user_id, role_id, site_id)
  WHERE site_id IS NOT NULL;

CREATE UNIQUE INDEX ux_user_roles_global
  ON user_roles(user_id, role_id)
  WHERE site_id IS NULL;

-- [FULL] JWT refresh token / 세션 종료 관리가 필요할 때 사용
-- 기능: 토큰 폐기, 강제 로그아웃, 다중 기기 세션 추적
CREATE TABLE auth_sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  refresh_token_hash TEXT NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);


-- =========================================================
-- [CORE] 파일 / 문서 저장
-- 기능: 작업허가서 PDF, 사진 신고, 영상 스냅샷, TTS 음성 저장
-- 요구사항 매칭:
-- - 허가서 신청 > 문서 첨부
-- - TBM 브리핑 > TTS 리딩
-- - 위험 신고 > 사진/음성 신고
-- - 영상 감시 > 프레임/마스킹 결과 저장
-- =========================================================

CREATE TABLE files (
  id BIGSERIAL PRIMARY KEY,
  uploaded_by BIGINT REFERENCES users(id),
  storage_key TEXT NOT NULL,
  original_name TEXT NOT NULL,
  mime_type VARCHAR(100),
  file_type VARCHAR(40) NOT NULL,
  file_size BIGINT,
  checksum VARCHAR(128),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- [CORE] 현장 / 블록 / 위험구역 / 카메라
-- 기능: 현장 구역, 위험구역, ROI, CCTV 위치 관리
-- 요구사항 매칭:
-- - 영상 감시 > ROI 침입 탐지
-- - 위험 예측 > 2.5D 모델맵
-- - 인프라/배포 > 모니터링, 실시간 스트림
-- =========================================================

CREATE TABLE blocks (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT NOT NULL REFERENCES sites(id),
  block_code VARCHAR(50) NOT NULL,
  grid_x INT,
  grid_y INT,
  polygon JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (site_id, block_code)
);

CREATE TABLE danger_zones (
  id BIGSERIAL PRIMARY KEY,
  block_id BIGINT NOT NULL REFERENCES blocks(id),
  zone_type VARCHAR(50) NOT NULL,
  polygon JSONB NOT NULL,
  threshold_score INT DEFAULT 70,
  access_limit INT,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cameras (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT NOT NULL REFERENCES sites(id),
  block_id BIGINT REFERENCES blocks(id),
  camera_code VARCHAR(50) NOT NULL,
  name VARCHAR(120),
  stream_url TEXT,
  edge_device VARCHAR(120),
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (site_id, camera_code)
);


-- =========================================================
-- [CORE] 작업허가서
-- 기능: 작업허가서 신청, 작업 내용/시간/위치/인원 저장
-- 요구사항 매칭:
-- - 허가서 신청 > 문서 첨부
-- - 허가서 분석 > 위험 조건 도출
-- - 조건 수신 > 체크리스트 조회
-- =========================================================

CREATE TABLE work_permits (
  id BIGSERIAL PRIMARY KEY,
  permit_no VARCHAR(80) UNIQUE,
  site_id BIGINT NOT NULL REFERENCES sites(id),
  block_id BIGINT REFERENCES blocks(id),
  applicant_id BIGINT NOT NULL REFERENCES users(id),
  work_type VARCHAR(80),
  work_title TEXT,
  work_content TEXT,
  worker_count INT,
  equipment TEXT,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  gps_lat NUMERIC(10, 7),
  gps_lng NUMERIC(10, 7),
  is_high_risk BOOLEAN NOT NULL DEFAULT false,
  status VARCHAR(30) NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE work_permit_files (
  permit_id BIGINT NOT NULL REFERENCES work_permits(id) ON DELETE CASCADE,
  file_id BIGINT NOT NULL REFERENCES files(id),
  purpose VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (permit_id, file_id)
);

-- [FULL] 허가서 PDF 분석 결과 저장
-- 기능: PDF에서 작업명/공종/위험요인/추천 조건을 추출하고 화면에 보여줌
-- 요구사항 매칭:
-- - 허가서 분석 > 통합 안전 기준 요약
-- - 허가서 분석 > 승인 조건 도출
CREATE TABLE permit_analysis_results (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT NOT NULL REFERENCES work_permits(id) ON DELETE CASCADE,
  analysis_type VARCHAR(50) NOT NULL,
  model_name VARCHAR(80),
  summary TEXT,
  extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  risk_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
  recommended_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
  confidence NUMERIC(5, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- [FULL] 유사 사고 검색 결과 저장
-- 기능: 중대재해 사례 검색, 유사사례를 허가서 검토 화면에 표시
-- 요구사항 매칭:
-- - 허가서 분석 > 유사사고 검색
CREATE TABLE similar_accident_results (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT NOT NULL REFERENCES work_permits(id) ON DELETE CASCADE,
  source_title TEXT,
  source_url TEXT,
  accident_type VARCHAR(80),
  similarity_score NUMERIC(6, 4),
  summary TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- [CORE] 안전 기준 / 룰 체크 / 체크리스트
-- 기능: 안전 기준 저장, 허가서 조건 검증, 작업자 확인 체크리스트
-- 요구사항 매칭:
-- - TBM 브리핑 > 안전용어 교정
-- - TBM 브리핑 > 다국어 번역
-- - 조건 수신 > 체크리스트 조회
-- - 조건 수신 > 긴급 알림
-- =========================================================

CREATE TABLE safety_rules (
  id BIGSERIAL PRIMARY KEY,
  rule_code VARCHAR(80) UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category VARCHAR(80),
  original_text TEXT NOT NULL,
  easy_text TEXT,
  language VARCHAR(20) DEFAULT 'ko',
  severity VARCHAR(30),
  source TEXT,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rule_checks (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT REFERENCES work_permits(id) ON DELETE CASCADE,
  rule_id BIGINT NOT NULL REFERENCES safety_rules(id),
  checker_type VARCHAR(30) NOT NULL DEFAULT 'ai',
  check_result VARCHAR(30) NOT NULL,
  result_score INT,
  evidence TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE checklist_templates (
  id BIGSERIAL PRIMARY KEY,
  site_id BIGINT REFERENCES sites(id),
  work_type VARCHAR(80),
  title VARCHAR(150) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE checklist_items (
  id BIGSERIAL PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES checklist_templates(id) ON DELETE CASCADE,
  rule_id BIGINT REFERENCES safety_rules(id),
  item_text TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_required BOOLEAN NOT NULL DEFAULT true
);


-- =========================================================
-- [CORE] TBM 브리핑
-- 기능: 작업 전 브리핑, 번역/쉬운 설명/TTS, 참석 확인
-- 요구사항 매칭:
-- - TBM 브리핑 > 한국어 음성인식
-- - TBM 브리핑 > 안전용어 교정
-- - TBM 브리핑 > 다국어 번역
-- - TBM 브리핑 > TTS 리딩
-- - TBM 브리핑 > 전달 확인
-- =========================================================

CREATE TABLE tbm_sessions (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT NOT NULL REFERENCES work_permits(id) ON DELETE CASCADE,
  host_id BIGINT REFERENCES users(id),
  title VARCHAR(150),
  session_date DATE NOT NULL DEFAULT CURRENT_DATE,
  status VARCHAR(30) NOT NULL DEFAULT 'planned',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tbm_materials (
  id BIGSERIAL PRIMARY KEY,
  tbm_session_id BIGINT NOT NULL REFERENCES tbm_sessions(id) ON DELETE CASCADE,
  material_type VARCHAR(50) NOT NULL,
  language VARCHAR(20) DEFAULT 'ko',
  content TEXT,
  file_id BIGINT REFERENCES files(id),
  model_name VARCHAR(80),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tbm_attendance (
  tbm_session_id BIGINT NOT NULL REFERENCES tbm_sessions(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id),
  confirmed_at TIMESTAMPTZ,
  signature_file_id BIGINT REFERENCES files(id),
  PRIMARY KEY (tbm_session_id, user_id)
);

CREATE TABLE checklist_responses (
  id BIGSERIAL PRIMARY KEY,
  tbm_session_id BIGINT NOT NULL REFERENCES tbm_sessions(id) ON DELETE CASCADE,
  checklist_item_id BIGINT NOT NULL REFERENCES checklist_items(id),
  responder_id BIGINT NOT NULL REFERENCES users(id),
  response_value VARCHAR(30) NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- [FULL] 승인 워크플로우
-- 기능: 관리자 조건 선택, 단계별 승인/반려, 승인 이력
-- 요구사항 매칭:
-- - 허가서 분석 > 승인 워크플로우
-- - 관리자기능 > 작업 허가서 조건 검토/승인
-- =========================================================

CREATE TABLE approval_flows (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT NOT NULL REFERENCES work_permits(id) ON DELETE CASCADE,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE approval_steps (
  id BIGSERIAL PRIMARY KEY,
  flow_id BIGINT NOT NULL REFERENCES approval_flows(id) ON DELETE CASCADE,
  step_order INT NOT NULL,
  approver_id BIGINT NOT NULL REFERENCES users(id),
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  condition_text TEXT,
  comment TEXT,
  decided_at TIMESTAMPTZ,
  UNIQUE (flow_id, step_order)
);


-- =========================================================
-- [FULL] 영상 감시 / 위험 이벤트
-- 기능: PPE 위반, ROI 침입, 작업자 미식별, 사진/음성 신고, 이벤트 처리 이력
-- 요구사항 매칭:
-- - 영상 감시 > PPE 위반 탐지
-- - 영상 감시 > 작업자 비식별화
-- - 영상 감시 > ROI 침입 탐지
-- - 영상 감시 > 관제 대시보드
-- - 위험 신고 > 사진/음성 신고
-- =========================================================

CREATE TABLE vision_detections (
  id BIGSERIAL PRIMARY KEY,
  camera_id BIGINT REFERENCES cameras(id),
  block_id BIGINT REFERENCES blocks(id),
  zone_id BIGINT REFERENCES danger_zones(id),
  file_id BIGINT REFERENCES files(id),
  detection_type VARCHAR(60) NOT NULL,
  object_label VARCHAR(80),
  confidence NUMERIC(5, 4),
  bbox JSONB,
  is_worker_identified BOOLEAN,
  worker_id BIGINT REFERENCES users(id),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE safety_events (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(60) NOT NULL,
  source_type VARCHAR(30) NOT NULL,
  reporter_id BIGINT REFERENCES users(id),
  permit_id BIGINT REFERENCES work_permits(id),
  block_id BIGINT REFERENCES blocks(id),
  zone_id BIGINT REFERENCES danger_zones(id),
  detection_id BIGINT REFERENCES vision_detections(id),
  file_id BIGINT REFERENCES files(id),
  severity VARCHAR(30) NOT NULL DEFAULT 'medium',
  title TEXT NOT NULL,
  description TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(30) NOT NULL DEFAULT 'open',
  event_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE event_actions (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES safety_events(id) ON DELETE CASCADE,
  actor_id BIGINT REFERENCES users(id),
  action_type VARCHAR(50) NOT NULL,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- [FULL] 위험 예측 / What-if 시뮬레이션
-- 기능: 위험도 산출, 2.5D 모델맵, 조치 변경 후 위험도 재계산
-- 요구사항 매칭:
-- - 위험 예측 > 위험도 산출
-- - 위험 예측 > 2.5D 모델맵
-- - 위험 예측 > What-if 재계산
-- =========================================================

CREATE TABLE risk_scores (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT REFERENCES work_permits(id),
  block_id BIGINT REFERENCES blocks(id),
  zone_id BIGINT REFERENCES danger_zones(id),
  event_id BIGINT REFERENCES safety_events(id),
  score INT NOT NULL CHECK (score BETWEEN 0 AND 100),
  risk_level VARCHAR(30) NOT NULL,
  model_name VARCHAR(80),
  factors JSONB NOT NULL DEFAULT '{}'::jsonb,
  shap_values JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE risk_simulations (
  id BIGSERIAL PRIMARY KEY,
  permit_id BIGINT REFERENCES work_permits(id),
  block_id BIGINT REFERENCES blocks(id),
  requested_by BIGINT REFERENCES users(id),
  scenario_type VARCHAR(50) NOT NULL,
  input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  before_score INT,
  after_score INT,
  result_summary TEXT,
  result_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  simulated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- [FULL] 알림 / 모델 운영 / 감사 로그
-- 기능: 앱 푸시, SNS, WebSocket, AI 추론 작업, 관리자 이력
-- 요구사항 매칭:
-- - 실시간 > API GW WebSocket
-- - 실시간 > 푸시 알림
-- - 인프라/배포 > 이벤트 스키마 확장
-- - 기준정보 > 감사 로그
-- =========================================================

CREATE TABLE notifications (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT REFERENCES safety_events(id),
  user_id BIGINT REFERENCES users(id),
  channel VARCHAR(30) NOT NULL,
  title TEXT NOT NULL,
  message TEXT,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_runs (
  id BIGSERIAL PRIMARY KEY,
  model_name VARCHAR(80) NOT NULL,
  model_version VARCHAR(50),
  input_type VARCHAR(50) NOT NULL,
  input_ref_id BIGINT,
  status VARCHAR(30) NOT NULL DEFAULT 'queued',
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT
);

CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  actor_id BIGINT REFERENCES users(id),
  action VARCHAR(80) NOT NULL,
  target_table VARCHAR(80),
  target_id BIGINT,
  before_data JSONB,
  after_data JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =========================================================
-- 조회 성능용 인덱스
-- =========================================================

CREATE INDEX idx_work_permits_site_status ON work_permits(site_id, status);
CREATE INDEX idx_work_permits_time ON work_permits(start_time, end_time);
CREATE INDEX idx_rule_checks_permit ON rule_checks(permit_id);
CREATE INDEX idx_safety_events_status_time ON safety_events(status, event_time DESC);
CREATE INDEX idx_vision_detections_time ON vision_detections(detected_at DESC);
CREATE INDEX idx_risk_scores_created ON risk_scores(created_at DESC);
CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
