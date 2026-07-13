package com.example.safetyai.risk;

import com.example.safetyai.auth.AuthService;
import com.example.safetyai.common.JdbcInsert;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
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
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/risks")
public class RiskController {
    private final JdbcTemplate jdbcTemplate;
    private final AuthService authService;

    public RiskController(JdbcTemplate jdbcTemplate, AuthService authService) {
        this.jdbcTemplate = jdbcTemplate;
        this.authService = authService;
    }

    @GetMapping("/scores")
    public List<Map<String, Object>> scores() {
        return jdbcTemplate.queryForList("SELECT * FROM risk_scores ORDER BY created_at DESC LIMIT 100");
    }

    @PostMapping("/scores")
    public Map<String, Object> createScore(@Valid @RequestBody RiskScoreRequest request) {
        long id = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO risk_scores
                (permit_id, block_id, zone_id, event_id, score, risk_level, model_name, factors, shap_values)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(
                request.permitId(),
                request.blockId(),
                request.zoneId(),
                request.eventId(),
                request.score(),
                request.riskLevel(),
                request.modelName(),
                request.factorsJson(),
                request.shapValuesJson()
            )
        );
        return Map.of("id", id);
    }

    @PostMapping("/simulations")
    public Map<String, Object> createSimulation(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @Valid @RequestBody RiskSimulationRequest request
    ) {
        long userId = authService.requireUserId(authorization);
        long id = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO risk_simulations
                (permit_id, block_id, requested_by, scenario_type, input_payload, before_score, after_score, result_summary, result_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(
                request.permitId(),
                request.blockId(),
                userId,
                request.scenarioType(),
                request.inputPayloadJson(),
                request.beforeScore(),
                request.afterScore(),
                request.resultSummary(),
                request.resultPayloadJson()
            )
        );
        return Map.of("id", id);
    }

    public record RiskScoreRequest(
        Long permitId,
        Long blockId,
        Long zoneId,
        Long eventId,
        @Min(0) @Max(100) Integer score,
        @NotBlank String riskLevel,
        String modelName,
        String factorsJson,
        String shapValuesJson
    ) {
        public RiskScoreRequest {
            if (factorsJson == null || factorsJson.isBlank()) {
                factorsJson = "{}";
            }
            if (shapValuesJson == null || shapValuesJson.isBlank()) {
                shapValuesJson = "{}";
            }
        }
    }

    public record RiskSimulationRequest(
        Long permitId,
        Long blockId,
        @NotBlank String scenarioType,
        String inputPayloadJson,
        Integer beforeScore,
        Integer afterScore,
        String resultSummary,
        String resultPayloadJson
    ) {
        public RiskSimulationRequest {
            if (inputPayloadJson == null || inputPayloadJson.isBlank()) {
                inputPayloadJson = "{}";
            }
            if (resultPayloadJson == null || resultPayloadJson.isBlank()) {
                resultPayloadJson = "{}";
            }
        }
    }
}
