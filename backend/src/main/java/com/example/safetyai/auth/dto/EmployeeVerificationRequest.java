package com.example.safetyai.auth.dto;

import jakarta.validation.constraints.NotBlank;

public record EmployeeVerificationRequest(
    @NotBlank String name,
    @NotBlank String employeeNo
) {
}
