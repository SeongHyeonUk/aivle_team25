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
import org.springframework.transaction.annotation.Transactional;
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
