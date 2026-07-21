package com.example.safetyai.permit.controller;

import com.example.safetyai.auth.service.AuthService;
import com.example.safetyai.common.exception.ApiException;
import com.example.safetyai.common.util.JdbcInsert;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/work-permits")
public class WorkPermitController {
    private final JdbcTemplate jdbcTemplate;
    private final AuthService authService;

    public WorkPermitController(JdbcTemplate jdbcTemplate, AuthService authService) {
        this.jdbcTemplate = jdbcTemplate;
        this.authService = authService;
    }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(required = false) String status) {
        if (status == null || status.isBlank()) {
            return jdbcTemplate.queryForList("SELECT * FROM work_permits ORDER BY created_at DESC");
        }
        return jdbcTemplate.queryForList("SELECT * FROM work_permits WHERE status = ? ORDER BY created_at DESC", status);
    }

    @GetMapping("/today")
    public Map<String, Object> today(@AuthenticationPrincipal AuthService.AuthenticatedUser user) {
        if (user == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
            """
                SELECT wp.*, s.name AS site_name, b.block_code,
                       (SELECT par.recommended_conditions
                          FROM permit_analysis_results par
                         WHERE par.permit_id = wp.id
                         ORDER BY par.created_at DESC
                         LIMIT 1) AS recommended_conditions
                  FROM work_permits wp
                  JOIN sites s ON s.id = wp.site_id
             LEFT JOIN blocks b ON b.id = wp.block_id
                 WHERE wp.status <> 'rejected'
                   AND (
                       DATE(wp.created_at) = CURRENT_DATE
                       OR (wp.start_time < CURRENT_DATE + INTERVAL 1 DAY
                           AND COALESCE(wp.end_time, wp.start_time) >= CURRENT_DATE)
                   )
                 ORDER BY CASE WHEN wp.start_time IS NULL THEN 1 ELSE 0 END,
                          wp.start_time DESC,
                          wp.created_at DESC
                 LIMIT 1
                """
        );
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable long id) {
        Map<String, Object> permit = jdbcTemplate.queryForMap("SELECT * FROM work_permits WHERE id = ?", id);
        permit.put("files", jdbcTemplate.queryForList(
            """
                SELECT f.id, f.original_name, f.file_type, f.file_size, pf.purpose
                FROM work_permit_files pf
                JOIN files f ON f.id = pf.file_id
                WHERE pf.permit_id = ?
                """,
            id
        ));
        permit.put("analysisResults", jdbcTemplate.queryForList(
            "SELECT * FROM permit_analysis_results WHERE permit_id = ? ORDER BY created_at DESC",
            id
        ));
        permit.put("riskScores", jdbcTemplate.queryForList(
            "SELECT * FROM risk_scores WHERE permit_id = ? ORDER BY created_at DESC",
            id
        ));
        return permit;
    }

    @PostMapping
    @Transactional
    public Map<String, Object> create(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @Valid @RequestBody WorkPermitRequest request
    ) {
        long userId = authService.requireUserId(authorization);
        long id = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO work_permits
                (permit_no, site_id, block_id, applicant_id, work_type, work_title, work_content,
                 worker_count, equipment, start_time, end_time, gps_lat, gps_lng, is_high_risk, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(
                request.permitNo(),
                request.siteId(),
                request.blockId(),
                userId,
                request.workType(),
                request.workTitle(),
                request.workContent(),
                request.workerCount(),
                request.equipment(),
                request.startTime(),
                request.endTime(),
                request.gpsLat(),
                request.gpsLng(),
                request.isHighRisk(),
                request.status()
            )
        );
        if (request.fileIds() != null) {
            for (Long fileId : request.fileIds()) {
                int linked = jdbcTemplate.update(
                    """
                        INSERT INTO work_permit_files (permit_id, file_id, purpose)
                        SELECT ?, id, 'permit' FROM files
                        WHERE id = ? AND uploaded_by = ? AND file_type = 'permit'
                        """,
                    id,
                    fileId,
                    userId
                );
                if (linked != 1) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "업로드한 허가서 파일을 찾을 수 없습니다.");
                }
            }
        }
        return Map.of("id", id);
    }

    @DeleteMapping("/{id}")
    @Transactional
    public Map<String, Object> delete(
        @AuthenticationPrincipal AuthService.AuthenticatedUser user,
        @PathVariable long id
    ) {
        if (user == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        List<Map<String, Object>> permits = jdbcTemplate.queryForList(
            "SELECT applicant_id FROM work_permits WHERE id = ?",
            id
        );
        if (permits.isEmpty()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "삭제할 허가서를 찾을 수 없습니다.");
        }

        long applicantId = ((Number) permits.get(0).get("applicant_id")).longValue();
        if (applicantId != user.id() && !user.roles().contains("SAFETY_MANAGER")) {
            throw new ApiException(HttpStatus.FORBIDDEN, "허가서를 삭제할 권한이 없습니다.");
        }

        Integer linkedEvents = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM safety_events WHERE permit_id = ?",
            Integer.class,
            id
        );
        if (linkedEvents != null && linkedEvents > 0) {
            throw new ApiException(HttpStatus.CONFLICT, "안전 이벤트에 연결된 허가서는 삭제할 수 없습니다.");
        }

        jdbcTemplate.update("DELETE FROM risk_simulations WHERE permit_id = ?", id);
        jdbcTemplate.update("DELETE FROM risk_scores WHERE permit_id = ?", id);
        jdbcTemplate.update("DELETE FROM work_permits WHERE id = ?", id);
        return Map.of("deleted", true, "id", id);
    }

    public record WorkPermitRequest(
        String permitNo,
        @NotNull Long siteId,
        Long blockId,
        String workType,
        String workTitle,
        String workContent,
        Integer workerCount,
        String equipment,
        LocalDateTime startTime,
        LocalDateTime endTime,
        Double gpsLat,
        Double gpsLng,
        Boolean isHighRisk,
        String status,
        List<Long> fileIds
    ) {
        public WorkPermitRequest {
            if (isHighRisk == null) {
                isHighRisk = false;
            }
            if (status == null || status.isBlank()) {
                status = "draft";
            }
        }
    }
}
