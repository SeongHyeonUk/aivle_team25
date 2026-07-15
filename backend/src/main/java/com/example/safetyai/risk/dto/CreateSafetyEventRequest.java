package com.example.safetyai.risk.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CreateSafetyEventRequest(
    @NotBlank String eventType,
    @NotNull Long fileId,
    @NotBlank @Size(max = 2000) String description
) {
}
