package com.example.safetyai.auth.controller;

import com.example.safetyai.auth.dto.EmployeeVerificationRequest;
import com.example.safetyai.auth.dto.LoginRequest;
import com.example.safetyai.auth.dto.RegisterRequest;
import com.example.safetyai.auth.service.AuthService;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public Map<String, Object> register(@Valid @RequestBody RegisterRequest request) {
        return authService.register(request);
    }

    @PostMapping("/employees/verify")
    public Map<String, Object> verifyEmployee(@Valid @RequestBody EmployeeVerificationRequest request) {
        return authService.verifyEmployee(request.name(), request.employeeNo());
    }

    @GetMapping("/usernames/{username}/availability")
    public Map<String, Object> checkUsernameAvailability(@PathVariable String username) {
        return authService.checkUsernameAvailability(username);
    }

    @PostMapping("/login")
    public Map<String, Object> login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @PostMapping("/logout")
    public Map<String, String> logout(@RequestHeader(value = "Authorization", required = false) String authorization) {
        authService.logout(authorization);
        return Map.of("status", "ok");
    }
}
