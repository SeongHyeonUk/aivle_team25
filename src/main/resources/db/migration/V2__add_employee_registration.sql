CREATE TABLE employees (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  employee_no VARCHAR(50) NOT NULL,
  name VARCHAR(80) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT ux_employees_employee_no UNIQUE (employee_no)
);

-- Local employee registry used by the registration verification flow.
-- Application accounts are intentionally not copied into this registry.
INSERT INTO employees (employee_no, name, status) VALUES
  ('A-0001', '이호', 'active');

ALTER TABLE users
  ADD COLUMN employee_id BIGINT NULL,
  ADD CONSTRAINT ux_users_employee_id UNIQUE (employee_id),
  ADD CONSTRAINT fk_users_employee_id FOREIGN KEY (employee_id) REFERENCES employees(id);

INSERT IGNORE INTO roles (role_code, name, description) VALUES
  ('WORKER', '현장 작업자', 'TBM, 체크리스트, 위험 신고 기능을 사용합니다.'),
  ('ADMIN', '관리자', '관제, 허가서, 위험 예측 기능을 관리합니다.');
