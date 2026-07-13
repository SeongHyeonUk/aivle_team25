package com.example.safetyai.auth;

import com.example.safetyai.common.ApiException;
import com.example.safetyai.common.JdbcInsert;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {
    private final JdbcTemplate jdbcTemplate;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public AuthService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Map<String, Object> register(RegisterRequest request) {
        long userId = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO users (employee_no, username, password_hash, name, phone, company_name)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(
                request.employeeNo(),
                request.username(),
                passwordEncoder.encode(request.password()),
                request.name(),
                request.phone(),
                request.companyName()
            )
        );
        return Map.of("id", userId, "username", request.username(), "name", request.name());
    }

    public Map<String, Object> login(LoginRequest request) {
        List<Map<String, Object>> users = jdbcTemplate.queryForList(
            "SELECT id, username, password_hash, name, status FROM users WHERE username = ?",
            request.username()
        );
        if (users.isEmpty()) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다.");
        }
        Map<String, Object> user = users.get(0);
        if (!"active".equals(String.valueOf(user.get("status")))
            || !passwordEncoder.matches(request.password(), String.valueOf(user.get("password_hash")))) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다.");
        }

        String token = UUID.randomUUID() + "." + UUID.randomUUID();
        LocalDateTime expiresAt = LocalDateTime.now().plusDays(14);
        JdbcInsert.insert(
            jdbcTemplate,
            "INSERT INTO auth_sessions (user_id, refresh_token_hash, expires_at) VALUES (?, ?, ?)",
            Arrays.asList(user.get("id"), sha256(token), expiresAt)
        );
        return Map.of(
            "tokenType", "Bearer",
            "accessToken", token,
            "expiresAt", expiresAt,
            "user", Map.of("id", user.get("id"), "username", user.get("username"), "name", user.get("name"))
        );
    }

    public void logout(String authorization) {
        String token = extractBearer(authorization);
        jdbcTemplate.update(
            "UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE refresh_token_hash = ? AND revoked_at IS NULL",
            sha256(token)
        );
    }

    public long requireUserId(String authorization) {
        String token = extractBearer(authorization);
        List<Long> ids = jdbcTemplate.query(
            """
                SELECT user_id FROM auth_sessions
                WHERE refresh_token_hash = ? AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
                """,
            (rs, rowNum) -> rs.getLong("user_id"),
            sha256(token)
        );
        if (ids.isEmpty()) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        }
        return ids.get(0);
    }

    private String extractBearer(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Bearer 토큰이 필요합니다.");
        }
        return authorization.substring("Bearer ".length()).trim();
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("토큰 해시 생성에 실패했습니다.", ex);
        }
    }

    public record RegisterRequest(
        String employeeNo,
        String username,
        String password,
        String name,
        String phone,
        String companyName
    ) {
    }

    public record LoginRequest(String username, String password) {
    }
}
