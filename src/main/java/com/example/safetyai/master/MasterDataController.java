package com.example.safetyai.master;

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
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/master")
public class MasterDataController {
    private final JdbcTemplate jdbcTemplate;

    public MasterDataController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/sites")
    public List<Map<String, Object>> sites() {
        return jdbcTemplate.queryForList("SELECT * FROM sites ORDER BY id DESC");
    }

    @PostMapping("/sites")
    public Map<String, Object> createSite(@Valid @RequestBody SiteRequest request) {
        long id = JdbcInsert.insert(
            jdbcTemplate,
            "INSERT INTO sites (site_code, name, address) VALUES (?, ?, ?)",
            Arrays.asList(request.siteCode(), request.name(), request.address())
        );
        return Map.of("id", id);
    }

    @GetMapping("/blocks")
    public List<Map<String, Object>> blocks() {
        return jdbcTemplate.queryForList("SELECT * FROM blocks ORDER BY id DESC");
    }

    @GetMapping("/cameras")
    public List<Map<String, Object>> cameras() {
        return jdbcTemplate.queryForList("SELECT * FROM cameras ORDER BY id DESC");
    }

    public record SiteRequest(@NotBlank String siteCode, @NotBlank String name, String address) {
    }
}
