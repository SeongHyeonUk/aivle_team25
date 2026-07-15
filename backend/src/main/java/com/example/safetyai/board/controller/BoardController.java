package com.example.safetyai.board.controller;

import com.example.safetyai.auth.service.AuthService;
import com.example.safetyai.common.util.JdbcInsert;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/board/posts")
public class BoardController {
    private final JdbcTemplate jdbcTemplate;
    private final AuthService authService;

    public BoardController(JdbcTemplate jdbcTemplate, AuthService authService) {
        this.jdbcTemplate = jdbcTemplate;
        this.authService = authService;
    }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(defaultValue = "general") String category) {
        return jdbcTemplate.queryForList(
            """
                SELECT p.id, p.category, p.title, p.view_count, p.created_at, u.name AS author_name
                FROM board_posts p
                JOIN users u ON u.id = p.author_id
                WHERE p.category = ? AND p.status = 'published'
                ORDER BY p.created_at DESC
                """,
            category
        );
    }

    @GetMapping("/{id}")
    @Transactional
    public Map<String, Object> get(@PathVariable long id) {
        jdbcTemplate.update("UPDATE board_posts SET view_count = view_count + 1 WHERE id = ?", id);
        Map<String, Object> post = jdbcTemplate.queryForMap(
            """
                SELECT p.*, u.name AS author_name
                FROM board_posts p
                JOIN users u ON u.id = p.author_id
                WHERE p.id = ? AND p.status = 'published'
                """,
            id
        );
        List<Map<String, Object>> comments = jdbcTemplate.queryForList(
            """
                SELECT c.id, c.content, c.created_at, u.name AS author_name
                FROM board_post_comments c
                JOIN users u ON u.id = c.author_id
                WHERE c.post_id = ? AND c.status = 'published'
                ORDER BY c.created_at
                """,
            id
        );
        List<Map<String, Object>> files = jdbcTemplate.queryForList(
            """
                SELECT f.id, f.original_name, f.file_type, f.file_size
                FROM board_post_files pf
                JOIN files f ON f.id = pf.file_id
                WHERE pf.post_id = ?
                """,
            id
        );
        post.put("comments", comments);
        post.put("files", files);
        return post;
    }

    @PostMapping
    @Transactional
    public Map<String, Object> create(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @Valid @RequestBody CreatePostRequest request
    ) {
        long userId = authService.requireUserId(authorization);
        long postId = JdbcInsert.insert(
            jdbcTemplate,
            "INSERT INTO board_posts (author_id, category, title, content) VALUES (?, ?, ?, ?)",
            List.of(userId, request.category(), request.title(), request.content())
        );
        List<Long> fileIds = request.fileIds() == null ? new ArrayList<>() : request.fileIds();
        for (Long fileId : fileIds) {
            jdbcTemplate.update("INSERT INTO board_post_files (post_id, file_id) VALUES (?, ?)", postId, fileId);
        }
        return Map.of("id", postId);
    }

    @PostMapping("/{id}/comments")
    public Map<String, Object> comment(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @PathVariable long id,
        @Valid @RequestBody CommentRequest request
    ) {
        long userId = authService.requireUserId(authorization);
        long commentId = JdbcInsert.insert(
            jdbcTemplate,
            "INSERT INTO board_post_comments (post_id, author_id, content) VALUES (?, ?, ?)",
            List.of(id, userId, request.content())
        );
        return Map.of("id", commentId);
    }

    public record CreatePostRequest(
        String category,
        @NotBlank String title,
        @NotBlank String content,
        List<Long> fileIds
    ) {
        public CreatePostRequest {
            if (category == null || category.isBlank()) {
                category = "general";
            }
        }
    }

    public record CommentRequest(@NotBlank String content) {
    }
}
