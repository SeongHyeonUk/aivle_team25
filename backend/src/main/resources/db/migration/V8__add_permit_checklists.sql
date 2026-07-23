CREATE TABLE permit_checklists (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  permit_id BIGINT NOT NULL,
  generated_by VARCHAR(50) NOT NULL DEFAULT 'permit-ai',
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT ux_permit_checklists_permit UNIQUE (permit_id),
  CONSTRAINT fk_permit_checklists_permit FOREIGN KEY (permit_id) REFERENCES work_permits(id) ON DELETE CASCADE
);

CREATE TABLE permit_checklist_items (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  checklist_id BIGINT NOT NULL,
  category VARCHAR(50) NOT NULL,
  item_text TEXT NOT NULL,
  sort_order INT NOT NULL,
  is_required BOOLEAN NOT NULL DEFAULT true,
  CONSTRAINT fk_permit_checklist_items_checklist FOREIGN KEY (checklist_id) REFERENCES permit_checklists(id) ON DELETE CASCADE
);

CREATE TABLE permit_checklist_submissions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  checklist_id BIGINT NOT NULL,
  responder_id BIGINT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'draft',
  submitted_at TIMESTAMP(6),
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT ux_permit_checklist_submission UNIQUE (checklist_id, responder_id),
  CONSTRAINT fk_permit_checklist_submissions_checklist FOREIGN KEY (checklist_id) REFERENCES permit_checklists(id) ON DELETE CASCADE,
  CONSTRAINT fk_permit_checklist_submissions_responder FOREIGN KEY (responder_id) REFERENCES users(id)
);

CREATE TABLE permit_checklist_responses (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  submission_id BIGINT NOT NULL,
  item_id BIGINT NOT NULL,
  checked BOOLEAN NOT NULL DEFAULT false,
  note TEXT,
  checked_at TIMESTAMP(6),
  CONSTRAINT ux_permit_checklist_response UNIQUE (submission_id, item_id),
  CONSTRAINT fk_permit_checklist_responses_submission FOREIGN KEY (submission_id) REFERENCES permit_checklist_submissions(id) ON DELETE CASCADE,
  CONSTRAINT fk_permit_checklist_responses_item FOREIGN KEY (item_id) REFERENCES permit_checklist_items(id) ON DELETE CASCADE
);
