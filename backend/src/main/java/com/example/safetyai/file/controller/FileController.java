package com.example.safetyai.file.controller;

import com.example.safetyai.auth.service.AuthService;
import com.example.safetyai.common.exception.ApiException;
import com.example.safetyai.common.util.JdbcInsert;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/files")
public class FileController {
    private static final long MAX_SAFETY_REPORT_IMAGE_SIZE = 10L * 1024L * 1024L;
    private static final Set<String> SAFETY_REPORT_IMAGE_TYPES = Set.of("image/jpeg", "image/png");

    private final JdbcTemplate jdbcTemplate;
    private final AuthService authService;
    private final Path uploadDir;

    public FileController(JdbcTemplate jdbcTemplate, AuthService authService, @Value("${app.upload-dir}") String uploadDir) {
        this.jdbcTemplate = jdbcTemplate;
        this.authService = authService;
        this.uploadDir = Path.of(uploadDir).toAbsolutePath().normalize();
    }

    @PostMapping
    public Map<String, Object> upload(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @RequestParam MultipartFile file,
        @RequestParam(defaultValue = "document") String fileType
    ) throws IOException {
        long userId = authService.requireUserId(authorization);
        validateUpload(file, fileType);
        Files.createDirectories(uploadDir);
        String storageName = UUID.randomUUID() + "-" + safeName(file.getOriginalFilename());
        Path target = uploadDir.resolve(storageName).normalize();
        file.transferTo(target);

        long id = JdbcInsert.insert(
            jdbcTemplate,
            """
                INSERT INTO files (uploaded_by, storage_key, original_name, mime_type, file_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
            Arrays.asList(userId, target.toString(), file.getOriginalFilename(), file.getContentType(), fileType, file.getSize())
        );
        return Map.of("id", id, "originalName", file.getOriginalFilename(), "fileType", fileType, "size", file.getSize());
    }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable long id) {
        return jdbcTemplate.queryForMap(
            """
                SELECT id, uploaded_by, original_name, mime_type, file_type, file_size, created_at
                FROM files WHERE id = ?
                """,
            id
        );
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<Resource> download(@PathVariable long id) throws IOException {
        Map<String, Object> row = jdbcTemplate.queryForMap(
            "SELECT storage_key, original_name, mime_type FROM files WHERE id = ?",
            id
        );
        Path path = Path.of(String.valueOf(row.get("storage_key"))).normalize();
        if (!Files.exists(path)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "파일을 찾을 수 없습니다.");
        }
        Resource resource = new UrlResource(path.toUri());
        String encodedName = URLEncoder.encode(String.valueOf(row.get("original_name")), StandardCharsets.UTF_8);
        String mimeType = row.get("mime_type") == null ? "application/octet-stream" : String.valueOf(row.get("mime_type"));
        return ResponseEntity.ok()
            .header(HttpHeaders.CONTENT_TYPE, mimeType)
            .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename(encodedName).build().toString())
            .body(resource);
    }

    private String safeName(String originalName) {
        if (originalName == null || originalName.isBlank()) {
            return "upload.bin";
        }
        return originalName.replaceAll("[\\\\/:*?\"<>|]", "_");
    }

    private void validateUpload(MultipartFile file, String fileType) {
        if (file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "첨부할 파일을 선택해 주세요.");
        }
        if (!"safety_report".equals(fileType)) {
            return;
        }
        if (file.getSize() > MAX_SAFETY_REPORT_IMAGE_SIZE) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "위험 신고 사진은 10MB 이하만 업로드할 수 있습니다.");
        }
        if (!SAFETY_REPORT_IMAGE_TYPES.contains(file.getContentType())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "위험 신고 사진은 JPG 또는 PNG 형식만 지원합니다.");
        }
    }
}
