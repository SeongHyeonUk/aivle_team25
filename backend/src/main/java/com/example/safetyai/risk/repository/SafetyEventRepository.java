package com.example.safetyai.risk.repository;

import com.example.safetyai.common.util.JdbcInsert;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class SafetyEventRepository {
    private final JdbcTemplate jdbcTemplate;

    public SafetyEventRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public long createUserReport(
        long reporterId,
        String eventType,
        long fileId,
        String title,
        String description
    ) {
        return JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO safety_events
                (event_type, source_type, reporter_id, file_id, severity, title, description, status)
                VALUES (?, 'user_report', ?, ?, 'medium', ?, ?, 'received')
                """,
            Arrays.asList(eventType, reporterId, fileId, title, description)
        );
    }

    public boolean isOwnedSafetyReportFile(long fileId, long userId) {
        Integer count = jdbcTemplate.queryForObject(
            """
                SELECT COUNT(*)
                FROM files
                WHERE id = ? AND uploaded_by = ? AND file_type = 'safety_report'
                """,
            Integer.class,
            fileId,
            userId
        );
        return count != null && count > 0;
    }

    public List<Map<String, Object>> findMyReports(long reporterId) {
        return jdbcTemplate.queryForList(
            """
                SELECT se.id,
                       CONCAT('SR-', DATE_FORMAT(se.event_time, '%Y'), '-', LPAD(se.id, 6, '0')) AS reportNo,
                       se.event_type AS eventType,
                       se.title,
                       se.description,
                       se.status,
                       se.severity,
                       se.event_time AS eventTime,
                       f.id AS fileId,
                       f.original_name AS originalName,
                       f.mime_type AS mimeType
                FROM safety_events se
                LEFT JOIN files f ON f.id = se.file_id
                WHERE se.reporter_id = ? AND se.source_type = 'user_report'
                ORDER BY se.event_time DESC
                LIMIT 20
                """,
            reporterId
        );
    }

    public List<Map<String, Object>> findAll(String status) {
        if (status == null || status.isBlank()) {
            return jdbcTemplate.queryForList("SELECT * FROM safety_events ORDER BY event_time DESC");
        }
        return jdbcTemplate.queryForList(
            "SELECT * FROM safety_events WHERE status = ? ORDER BY event_time DESC",
            status
        );
    }
}
