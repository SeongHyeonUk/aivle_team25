package com.example.safetyai.auth;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
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
        return authService.register(new AuthService.RegisterRequest(
            request.employeeNo(),
            request.username(),
            request.password(),
            request.passwordConfirm(),
            request.name()
        ));
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
        return authService.login(new AuthService.LoginRequest(request.username(), request.password()));
    }

    @PostMapping("/logout")
    public Map<String, String> logout(@RequestHeader(value = "Authorization", required = false) String authorization) {
        authService.logout(authorization);
        return Map.of("status", "ok");
    }

    public record RegisterRequest(
        @NotBlank String employeeNo,
        @NotBlank
        @Size(min = 4, max = 30)
        @Pattern(regexp = "^[A-Za-z0-9._-]+$", message = "영문, 숫자, ., _, -만 사용할 수 있습니다.")
        String username,
        @NotBlank @Size(min = 8, max = 72) String password,
        @NotBlank String passwordConfirm,
        @NotBlank String name
    ) {
    }

    public record EmployeeVerificationRequest(@NotBlank String name, @NotBlank String employeeNo) {
    }

    public record LoginRequest(@NotBlank String username, @NotBlank String password) {
    }
}
