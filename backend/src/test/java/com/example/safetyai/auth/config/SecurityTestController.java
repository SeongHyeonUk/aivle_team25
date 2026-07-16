package com.example.safetyai.auth.config;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class SecurityTestController {
    @GetMapping({"/api/master/sites", "/api/dashboard/summary", "/api/ai/model-runs"})
    Map<String, String> get() {
        return Map.of("status", "ok");
    }

    @PostMapping({"/api/master/sites", "/api/ai/model-runs"})
    Map<String, String> post() {
        return Map.of("status", "ok");
    }
}
