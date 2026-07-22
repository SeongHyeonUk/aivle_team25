package com.example.safetyai.auth.config;

import com.example.safetyai.auth.security.BearerTokenAuthenticationFilter;
import jakarta.servlet.http.HttpServletResponse;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
public class SecurityConfig {
    private final BearerTokenAuthenticationFilter bearerTokenAuthenticationFilter;

    public SecurityConfig(BearerTokenAuthenticationFilter bearerTokenAuthenticationFilter) {
        this.bearerTokenAuthenticationFilter = bearerTokenAuthenticationFilter;
    }

    @Bean
    public static PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .formLogin(form -> form.disable())
            .httpBasic(basic -> basic.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .requestMatchers("/api/health", "/api/auth/register", "/api/auth/login").permitAll()
                .requestMatchers("/api/auth/employees/verify", "/api/auth/usernames/*/availability").permitAll()

                // Master data may be read by signed-in users, but only administrators may change it.
                .requestMatchers(HttpMethod.POST, "/api/master/**").hasRole("ADMIN")

                // Operational dashboards and the complete event feed contain site-wide information.
                .requestMatchers("/api/dashboard/**").hasAnyRole("ADMIN", "SAFETY_MANAGER")
                .requestMatchers("/api/digital-twin/**").hasAnyRole("ADMIN", "SAFETY_MANAGER")
                .requestMatchers(HttpMethod.GET, "/api/safety-events").hasAnyRole("ADMIN", "SAFETY_MANAGER")
                .requestMatchers(HttpMethod.GET, "/api/safety-events/reports").hasAnyRole("ADMIN", "SAFETY_MANAGER")
                .requestMatchers(HttpMethod.POST, "/api/safety-events/*/actions").hasAnyRole("ADMIN", "SAFETY_MANAGER")

                // AI_SERVICE is a machine account used only to submit model outputs.
                .requestMatchers(HttpMethod.POST, "/api/ai/**").hasAnyRole("ADMIN", "AI_SERVICE")
                .requestMatchers(HttpMethod.GET, "/api/ai/**").hasAnyRole("ADMIN", "SAFETY_MANAGER")
                .requestMatchers(HttpMethod.POST, "/api/risks/scores").hasAnyRole("ADMIN", "AI_SERVICE")
                .requestMatchers(HttpMethod.GET, "/api/risks/scores").hasAnyRole("ADMIN", "SAFETY_MANAGER")

                // Reports, permits, simulations, files, and board features remain available to every
                // authenticated account. Resource-level ownership rules are handled separately.
                .anyRequest().authenticated()
            )
            .exceptionHandling(exceptions -> exceptions
                .authenticationEntryPoint((request, response, exception) -> {
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"message\":\"로그인이 필요합니다.\"}");
                })
                .accessDeniedHandler((request, response, exception) -> {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"message\":\"접근 권한이 없습니다.\"}");
                })
            )
            .addFilterBefore(bearerTokenAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(List.of("http://localhost:*", "http://127.0.0.1:*"));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        configuration.setExposedHeaders(List.of("Authorization"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
