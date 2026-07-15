package com.example.safetyai.auth.repository;

import com.example.safetyai.auth.entity.EmployeeEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EmployeeRepository extends JpaRepository<EmployeeEntity, Long> {
    Optional<EmployeeEntity> findByEmployeeNoAndNameAndStatus(String employeeNo, String name, String status);
}
