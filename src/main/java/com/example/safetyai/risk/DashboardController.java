package com.example.safetyai.risk;

import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {
    private final JdbcTemplate jdbcTemplate;

    public DashboardController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/summary")
    public Map<String, Object> summary() {
        return Map.of(
            "users", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM users", Long.class),
            "workPermits", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM work_permits", Long.class),
            "openEvents", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM safety_events WHERE status = 'open'", Long.class),
            "highRiskPermits", jdbcTemplate.queryForObject("SELECT COUNT(*) FROM work_permits WHERE is_high_risk = true", Long.class),
            "latestEvents", jdbcTemplate.queryForList("SELECT * FROM safety_events ORDER BY event_time DESC LIMIT 10"),
            "latestRiskScores", jdbcTemplate.queryForList("SELECT * FROM risk_scores ORDER BY created_at DESC LIMIT 10")
        );
    }
}
