package com.example.safetyai.auth.repository;

import com.example.safetyai.auth.entity.UserEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<UserEntity, Long> {
    boolean existsByEmployeeIdOrEmployeeNo(Long employeeId, String employeeNo);

    boolean existsByUsername(String username);

    Optional<UserEntity> findByUsername(String username);
}
