package com.example.safetyai.checklist.controller;

import com.example.safetyai.auth.service.AuthService;
import com.example.safetyai.common.exception.ApiException;
import com.example.safetyai.common.util.JdbcInsert;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class PermitChecklistController {
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public PermitChecklistController(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/work-permits/{permitId}/approve")
    @Transactional
    public Map<String, Object> approve(
        @AuthenticationPrincipal AuthService.AuthenticatedUser user,
        @PathVariable long permitId
    ) {
        requireManager(user);
        List<Map<String, Object>> permits = jdbcTemplate.queryForList(
            """
                SELECT wp.id, wp.permit_no, wp.work_type, wp.work_title, wp.work_content,
                       (SELECT par.recommended_conditions FROM permit_analysis_results par
                         WHERE par.permit_id = wp.id ORDER BY par.created_at DESC LIMIT 1) AS recommended_conditions
                  FROM work_permits wp WHERE wp.id = ?
                """,
            permitId
        );
        if (permits.isEmpty()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "작업허가서를 찾을 수 없습니다.");
        }

        jdbcTemplate.update("UPDATE work_permits SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", permitId);
        Long checklistId = jdbcTemplate.query(
            "SELECT id FROM permit_checklists WHERE permit_id = ?",
            resultSet -> resultSet.next() ? resultSet.getLong(1) : null,
            permitId
        );
        if (checklistId == null) {
            checklistId = JdbcInsert.insert(
                jdbcTemplate,
                "INSERT INTO permit_checklists (permit_id, generated_by) VALUES (?, 'permit-ai')",
                List.of(permitId)
            );
            List<GeneratedItem> items = generateItems(permits.get(0));
            for (int index = 0; index < items.size(); index++) {
                GeneratedItem item = items.get(index);
                jdbcTemplate.update(
                    "INSERT INTO permit_checklist_items (checklist_id, category, item_text, sort_order, is_required) VALUES (?, ?, ?, ?, true)",
                    checklistId,
                    item.category(),
                    item.text(),
                    index + 1
                );
            }
        }
        return Map.of("permitId", permitId, "status", "approved", "checklistId", checklistId);
    }

    @GetMapping("/checklists/today")
    public Map<String, Object> today(@AuthenticationPrincipal AuthService.AuthenticatedUser user) {
        requireUser(user);
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
            """
                SELECT pc.id, wp.id AS permit_id, wp.permit_no, wp.work_title, wp.work_type,
                       COALESCE(pcs.status, 'draft') AS submission_status, pcs.submitted_at
                  FROM permit_checklists pc
                  JOIN work_permits wp ON wp.id = pc.permit_id
             LEFT JOIN permit_checklist_submissions pcs ON pcs.checklist_id = pc.id AND pcs.responder_id = ?
                 WHERE wp.status IN ('approved', 'conditionally_approved')
                   AND (DATE(wp.created_at) = CURRENT_DATE OR
                        (wp.start_time < CURRENT_DATE + INTERVAL 1 DAY AND COALESCE(wp.end_time, wp.start_time) >= CURRENT_DATE))
                 ORDER BY wp.created_at DESC LIMIT 1
                """,
            user.id()
        );
        if (rows.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> checklist = rows.get(0);
        long checklistId = ((Number) checklist.get("id")).longValue();
        checklist.put("items", jdbcTemplate.queryForList(
            """
                SELECT pci.id, pci.category, pci.item_text, pci.sort_order, pci.is_required,
                       COALESCE(pcr.checked, false) AS checked, pcr.note
                  FROM permit_checklist_items pci
             LEFT JOIN permit_checklist_submissions pcs ON pcs.checklist_id = pci.checklist_id AND pcs.responder_id = ?
             LEFT JOIN permit_checklist_responses pcr ON pcr.submission_id = pcs.id AND pcr.item_id = pci.id
                 WHERE pci.checklist_id = ? ORDER BY pci.sort_order
                """,
            user.id(), checklistId
        ));
        return checklist;
    }

    @PostMapping("/checklists/{checklistId}/submit")
    @Transactional
    public Map<String, Object> submit(
        @AuthenticationPrincipal AuthService.AuthenticatedUser user,
        @PathVariable long checklistId,
        @RequestBody SubmitRequest request
    ) {
        requireUser(user);
        List<Long> requiredIds = jdbcTemplate.queryForList(
            "SELECT id FROM permit_checklist_items WHERE checklist_id = ? AND is_required = true ORDER BY sort_order",
            Long.class,
            checklistId
        );
        if (requiredIds.isEmpty()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "제출할 체크리스트가 없습니다.");
        }
        LinkedHashSet<Long> checkedIds = new LinkedHashSet<>(request.checkedItemIds() == null ? List.of() : request.checkedItemIds());
        if (!checkedIds.containsAll(requiredIds)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "필수 체크리스트 항목을 모두 확인해 주세요.");
        }

        jdbcTemplate.update(
            """
                INSERT INTO permit_checklist_submissions (checklist_id, responder_id, status)
                VALUES (?, ?, 'draft')
                ON DUPLICATE KEY UPDATE status = IF(status = 'submitted', status, 'draft')
                """,
            checklistId, user.id()
        );
        long submissionId = jdbcTemplate.queryForObject(
            "SELECT id FROM permit_checklist_submissions WHERE checklist_id = ? AND responder_id = ?",
            Long.class,
            checklistId, user.id()
        );
        for (Long itemId : requiredIds) {
            jdbcTemplate.update(
                """
                    INSERT INTO permit_checklist_responses (submission_id, item_id, checked, checked_at)
                    VALUES (?, ?, true, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE checked = true, checked_at = CURRENT_TIMESTAMP
                    """,
                submissionId, itemId
            );
        }
        jdbcTemplate.update(
            "UPDATE permit_checklist_submissions SET status = 'submitted', submitted_at = CURRENT_TIMESTAMP WHERE id = ?",
            submissionId
        );
        return Map.of("submissionId", submissionId, "status", "submitted");
    }

    private List<GeneratedItem> generateItems(Map<String, Object> permit) {
        LinkedHashSet<GeneratedItem> items = new LinkedHashSet<>();
        items.add(new GeneratedItem("공통", "작업 내용과 작업구역을 확인하고 출입 통제 상태를 점검했습니다."));
        items.add(new GeneratedItem("보호구", "작업에 필요한 개인보호구를 올바르게 착용했습니다."));
        items.add(new GeneratedItem("비상대응", "비상 연락망과 대피 경로, 소화·구조 장비 위치를 확인했습니다."));

        String work = String.join(" ",
            String.valueOf(permit.getOrDefault("work_type", "")),
            String.valueOf(permit.getOrDefault("work_title", "")),
            String.valueOf(permit.getOrDefault("work_content", ""))
        );
        if (work.contains("화기") || work.contains("용접")) {
            items.add(new GeneratedItem("화기", "화기감시자를 배치하고 소화기와 불티 비산 방지포를 준비했습니다."));
            items.add(new GeneratedItem("화기", "가연성 물질을 제거하고 작업 종료 후 잔불 점검 계획을 확인했습니다."));
        }
        if (work.contains("고소") || work.contains("높이")) {
            items.add(new GeneratedItem("고소", "안전대와 생명줄 체결 상태 및 추락 방지 시설을 확인했습니다."));
            items.add(new GeneratedItem("고소", "작업구역 하부 출입 통제선과 낙하물 방지 조치를 설치했습니다."));
        }
        if (work.contains("밀폐")) {
            items.add(new GeneratedItem("밀폐공간", "산소·유해가스 농도를 측정하고 환기 상태를 확인했습니다."));
            items.add(new GeneratedItem("밀폐공간", "감시인 배치와 구조장비 및 비상구조 절차를 확인했습니다."));
        }
        if (work.contains("전기")) {
            items.add(new GeneratedItem("전기", "전원 차단과 잠금표지(LOTO) 및 검전 상태를 확인했습니다."));
        }
        if (work.contains("중량") || work.contains("인양") || work.contains("크레인")) {
            items.add(new GeneratedItem("인양", "인양 장비의 정격하중과 와이어·슬링 상태를 확인했습니다."));
            items.add(new GeneratedItem("인양", "신호수를 지정하고 인양 반경 내 출입을 통제했습니다."));
        }

        addRecommendedConditions(items, permit.get("recommended_conditions"));
        return new ArrayList<>(items);
    }

    private void addRecommendedConditions(LinkedHashSet<GeneratedItem> items, Object raw) {
        if (raw == null) return;
        try {
            JsonNode node = objectMapper.readTree(String.valueOf(raw));
            if (node.isArray()) {
                node.forEach(value -> {
                    String text = value.isTextual() ? value.asText() : value.path("text").asText();
                    if (!text.isBlank()) items.add(new GeneratedItem("AI 승인조건", text));
                });
            }
        } catch (Exception ignored) {
            String text = String.valueOf(raw).trim();
            if (!text.isBlank() && !"null".equalsIgnoreCase(text)) items.add(new GeneratedItem("AI 승인조건", text));
        }
    }

    private void requireManager(AuthService.AuthenticatedUser user) {
        requireUser(user);
        if (!user.roles().contains("ADMIN") && !user.roles().contains("SAFETY_MANAGER")) {
            throw new ApiException(HttpStatus.FORBIDDEN, "작업허가서 승인 권한이 없습니다.");
        }
    }

    private void requireUser(AuthService.AuthenticatedUser user) {
        if (user == null) throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
    }

    public record SubmitRequest(List<Long> checkedItemIds) {
    }

    private record GeneratedItem(String category, String text) {
    }
}
