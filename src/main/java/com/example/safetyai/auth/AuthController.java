package com.example.safetyai.auth;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.Map;
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
        return authService.register(new AuthService.RegisterRequest(
            request.employeeNo(),
            request.username(),
            request.password(),
            request.name(),
            request.phone(),
            request.companyName()
        ));
    }

    @PostMapping("/login")
    public Map<String, Object> login(@Valid @RequestBody LoginRequest request) {
        return authService.login(new AuthService.LoginRequest(request.username(), request.password()));
    }

    @PostMapping("/logout")
    public Map<String, String> logout(@RequestHeader(value = "Authorization", required = false) String authorization) {
        authService.logout(authorization);
        return Map.of("status", "ok");
    }

    public record RegisterRequest(
        String employeeNo,
        @NotBlank String username,
        @NotBlank String password,
        @NotBlank String name,
        String phone,
        String companyName
    ) {
    }

    public record LoginRequest(@NotBlank String username, @NotBlank String password) {
    }
}
