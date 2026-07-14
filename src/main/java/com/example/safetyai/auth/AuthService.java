package com.example.safetyai.auth;

import com.example.safetyai.common.ApiException;
import com.example.safetyai.common.JdbcInsert;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final JdbcTemplate jdbcTemplate;
    private final PasswordEncoder passwordEncoder;

    public AuthService(JdbcTemplate jdbcTemplate, PasswordEncoder passwordEncoder) {
        this.jdbcTemplate = jdbcTemplate;
        this.passwordEncoder = passwordEncoder;
    }

    public Map<String, Object> verifyEmployee(String name, String employeeNo) {
        Employee employee = findActiveEmployee(name, employeeNo)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "이름과 사번이 일치하는 재직자를 찾을 수 없습니다."));
        if (isEmployeeClaimed(employee.id(), employee.employeeNo())) {
            throw new ApiException(HttpStatus.CONFLICT, "이미 가입된 사번입니다.");
        }
        return Map.of("verified", true, "employeeNo", employee.employeeNo(), "name", employee.name());
    }

    public Map<String, Object> checkUsernameAvailability(String username) {
        String normalized = normalizeUsername(username);
        validateUsername(normalized);
        boolean available = !usernameExists(normalized);
        return Map.of("available", available, "username", normalized);
    }

    @Transactional
    public Map<String, Object> register(RegisterRequest request) {
        String name = request.name().trim();
        String employeeNo = request.employeeNo().trim();
        String username = normalizeUsername(request.username());

        validateUsername(username);
        validatePassword(request.password(), request.passwordConfirm());

        Employee employee = findActiveEmployee(name, employeeNo)
            .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "사번 인증이 필요합니다."));
        if (isEmployeeClaimed(employee.id(), employee.employeeNo())) {
            throw new ApiException(HttpStatus.CONFLICT, "이미 가입된 사번입니다.");
        }
        if (usernameExists(username)) {
            throw new ApiException(HttpStatus.CONFLICT, "이미 사용 중인 아이디입니다.");
        }

        long userId = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO users (employee_id, employee_no, username, password_hash, name, status)
                VALUES (?, ?, ?, ?, ?, 'active')
                """,
            Arrays.asList(
                employee.id(),
                employee.employeeNo(),
                username,
                passwordEncoder.encode(request.password()),
                employee.name()
            )
        );

        int assignedRoles = jdbcTemplate.update(
            """
                INSERT INTO user_roles (user_id, role_id, site_id)
                SELECT ?, id, NULL FROM roles WHERE role_code = 'WORKER'
                """,
            userId
        );
        if (assignedRoles != 1) {
            throw new IllegalStateException("기본 WORKER 역할이 준비되지 않았습니다.");
        }

        return Map.of(
            "id", userId,
            "employeeNo", employee.employeeNo(),
            "username", username,
            "name", employee.name(),
            "roles", List.of("WORKER")
        );
    }

    public Map<String, Object> login(LoginRequest request) {
        String username = normalizeUsername(request.username());
        List<Map<String, Object>> users = jdbcTemplate.queryForList(
            "SELECT id, username, password_hash, name, status FROM users WHERE username = ?",
            username
        );
        if (users.isEmpty()) {
            throw invalidCredentials();
        }
        Map<String, Object> user = users.get(0);
        if (!"active".equals(String.valueOf(user.get("status")))
            || !passwordEncoder.matches(request.password(), String.valueOf(user.get("password_hash")))) {
            throw invalidCredentials();
        }

        long userId = ((Number) user.get("id")).longValue();
        List<String> roles = findRoleCodes(userId);
        String token = UUID.randomUUID() + "." + UUID.randomUUID();
        LocalDateTime expiresAt = LocalDateTime.now().plusDays(14);
        JdbcInsert.insert(
            jdbcTemplate,
            "INSERT INTO auth_sessions (user_id, refresh_token_hash, expires_at) VALUES (?, ?, ?)",
            Arrays.asList(userId, sha256(token), expiresAt)
        );
        return Map.of(
            "tokenType", "Bearer",
            "accessToken", token,
            "expiresAt", expiresAt,
            "user", Map.of(
                "id", userId,
                "username", user.get("username"),
                "name", user.get("name"),
                "roles", roles
            )
        );
    }

    public void logout(String authorization) {
        String token = extractBearer(authorization);
        jdbcTemplate.update(
            "UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE refresh_token_hash = ? AND revoked_at IS NULL",
            sha256(token)
        );
    }

    public Optional<AuthenticatedUser> authenticateBearer(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return Optional.empty();
        }
        String token = authorization.substring("Bearer ".length()).trim();
        if (token.isEmpty()) {
            return Optional.empty();
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
            """
                SELECT u.id, u.username, u.name
                FROM auth_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > CURRENT_TIMESTAMP
                  AND u.status = 'active'
                """,
            sha256(token)
        );
        if (rows.isEmpty()) {
            return Optional.empty();
        }
        Map<String, Object> row = rows.get(0);
        long userId = ((Number) row.get("id")).longValue();
        return Optional.of(new AuthenticatedUser(
            userId,
            String.valueOf(row.get("username")),
            String.valueOf(row.get("name")),
            findRoleCodes(userId)
        ));
    }

    public long requireUserId(String authorization) {
        return authenticateBearer(authorization)
            .map(AuthenticatedUser::id)
            .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."));
    }

    private Optional<Employee> findActiveEmployee(String name, String employeeNo) {
        String normalizedName = name == null ? "" : name.trim();
        String normalizedEmployeeNo = employeeNo == null ? "" : employeeNo.trim();
        return jdbcTemplate.query(
            """
                SELECT id, employee_no, name
                FROM employees
                WHERE employee_no = ? AND name = ? AND status = 'active'
                """,
            (rs, rowNum) -> new Employee(rs.getLong("id"), rs.getString("employee_no"), rs.getString("name")),
            normalizedEmployeeNo,
            normalizedName
        ).stream().findFirst();
    }

    private boolean isEmployeeClaimed(long employeeId, String employeeNo) {
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM users WHERE employee_id = ? OR employee_no = ?",
            Integer.class,
            employeeId,
            employeeNo
        );
        return count != null && count > 0;
    }

    private boolean usernameExists(String username) {
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            Integer.class,
            username
        );
        return count != null && count > 0;
    }

    private List<String> findRoleCodes(long userId) {
        return jdbcTemplate.queryForList(
            """
                SELECT r.role_code
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = ?
                ORDER BY r.role_code
                """,
            String.class,
            userId
        );
    }

    private String normalizeUsername(String username) {
        return username == null ? "" : username.trim().toLowerCase(Locale.ROOT);
    }

    private void validateUsername(String username) {
        if (!username.matches("^[A-Za-z0-9._-]{4,30}$")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "아이디는 4~30자의 영문, 숫자, ., _, -만 사용할 수 있습니다.");
        }
    }

    private void validatePassword(String password, String passwordConfirm) {
        if (!password.equals(passwordConfirm)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "비밀번호가 일치하지 않습니다.");
        }
        if (password.length() < 8 || password.getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "비밀번호는 8자 이상, UTF-8 기준 72바이트 이하여야 합니다.");
        }
    }

    private ApiException invalidCredentials() {
        return new ApiException(HttpStatus.UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다.");
    }

    private String extractBearer(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Bearer 토큰이 필요합니다.");
        }
        String token = authorization.substring("Bearer ".length()).trim();
        if (token.isEmpty()) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Bearer 토큰이 필요합니다.");
        }
        return token;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("토큰 해시 생성에 실패했습니다.", ex);
        }
    }

    private record Employee(long id, String employeeNo, String name) {
    }

    public record AuthenticatedUser(long id, String username, String name, List<String> roles) {
    }

    public record RegisterRequest(
        String employeeNo,
        String username,
        String password,
        String passwordConfirm,
        String name
    ) {
    }

    public record LoginRequest(String username, String password) {
    }
}
