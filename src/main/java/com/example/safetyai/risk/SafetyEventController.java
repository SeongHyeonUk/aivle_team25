package com.example.safetyai.risk;

import com.example.safetyai.auth.AuthService;
import com.example.safetyai.common.JdbcInsert;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/safety-events")
public class SafetyEventController {
    private final JdbcTemplate jdbcTemplate;
    private final AuthService authService;

    public SafetyEventController(JdbcTemplate jdbcTemplate, AuthService authService) {
        this.jdbcTemplate = jdbcTemplate;
        this.authService = authService;
    }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(required = false) String status) {
        if (status == null || status.isBlank()) {
            return jdbcTemplate.queryForList("SELECT * FROM safety_events ORDER BY event_time DESC");
        }
        return jdbcTemplate.queryForList("SELECT * FROM safety_events WHERE status = ? ORDER BY event_time DESC", status);
    }

    @PostMapping
    public Map<String, Object> create(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @Valid @RequestBody SafetyEventRequest request
    ) {
        long reporterId = authService.requireUserId(authorization);
        long id = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO safety_events
                (event_type, source_type, reporter_id, permit_id, block_id, zone_id, file_id, severity, title, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(
                request.eventType(),
                request.sourceType(),
                reporterId,
                request.permitId(),
                request.blockId(),
                request.zoneId(),
                request.fileId(),
                request.severity(),
                request.title(),
                request.description()
            )
        );
        return Map.of("id", id);
    }

    public record SafetyEventRequest(
        @NotBlank String eventType,
        String sourceType,
        Long permitId,
        Long blockId,
        Long zoneId,
        Long fileId,
        String severity,
        @NotBlank String title,
        String description
    ) {
        public SafetyEventRequest {
            if (sourceType == null || sourceType.isBlank()) {
                sourceType = "user";
            }
            if (severity == null || severity.isBlank()) {
                severity = "medium";
            }
        }
    }
}
