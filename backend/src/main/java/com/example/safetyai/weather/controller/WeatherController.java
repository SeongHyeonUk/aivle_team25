package com.example.safetyai.weather.controller;

import com.fasterxml.jackson.databind.JsonNode;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/weather")
public class WeatherController {
    private static final ZoneId KST = ZoneId.of("Asia/Seoul");
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HHmm");
    private static final Duration CACHE_TTL = Duration.ofMinutes(10);

    private final RestClient restClient = RestClient.create();
    private final String serviceKey;
    private final int gridX;
    private final int gridY;
    private volatile CachedWeather cache;

    public WeatherController(
        @Value("${app.weather.kma-service-key:}") String serviceKey,
        @Value("${app.weather.grid-x:90}") int gridX,
        @Value("${app.weather.grid-y:69}") int gridY
    ) {
        this.serviceKey = serviceKey.trim();
        this.gridX = gridX;
        this.gridY = gridY;
    }

    @GetMapping("/current")
    public WeatherResponse current() {
        if (serviceKey.isBlank()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "기상청 API 인증키가 설정되지 않았습니다.");
        }

        CachedWeather cached = cache;
        LocalDateTime now = LocalDateTime.now(KST);
        if (cached != null && Duration.between(cached.cachedAt(), now).compareTo(CACHE_TTL) < 0) {
            return cached.weather();
        }

        try {
            WeatherResponse weather = requestForecast(now);
            cache = new CachedWeather(now, weather);
            return weather;
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "기상청 날씨 정보를 불러오지 못했습니다.", exception);
        }
    }

    private WeatherResponse requestForecast(LocalDateTime now) {
        LocalDateTime base = now.getMinute() >= 45
            ? now.withMinute(30).withSecond(0).withNano(0)
            : now.minusHours(1).withMinute(30).withSecond(0).withNano(0);

        String encodedKey = URLEncoder.encode(serviceKey, StandardCharsets.UTF_8);
        URI uri = URI.create(
            "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
                + "?serviceKey=" + encodedKey
                + "&pageNo=1&numOfRows=1000&dataType=JSON"
                + "&base_date=" + base.format(DATE)
                + "&base_time=" + base.format(TIME)
                + "&nx=" + gridX + "&ny=" + gridY
        );

        JsonNode root = restClient.get().uri(uri).retrieve().body(JsonNode.class);
        String resultCode = root == null ? null : root.path("response").path("header").path("resultCode").asText();
        if (!"00".equals(resultCode)) {
            String message = root == null ? "응답 없음" : root.path("response").path("header").path("resultMsg").asText();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "기상청 API 오류: " + message);
        }

        JsonNode items = root.path("response").path("body").path("items").path("item");
        Map<LocalDateTime, Map<String, String>> forecasts = new HashMap<>();
        for (Iterator<JsonNode> iterator = items.elements(); iterator.hasNext();) {
            JsonNode item = iterator.next();
            LocalDateTime forecastAt = LocalDateTime.of(
                LocalDate.parse(item.path("fcstDate").asText(), DATE),
                LocalTime.parse(item.path("fcstTime").asText(), TIME)
            );
            forecasts.computeIfAbsent(forecastAt, ignored -> new HashMap<>())
                .put(item.path("category").asText(), item.path("fcstValue").asText());
        }

        Map.Entry<LocalDateTime, Map<String, String>> selected = forecasts.entrySet().stream()
            .filter(entry -> !entry.getKey().isBefore(now.withMinute(0).withSecond(0).withNano(0)))
            .min(Map.Entry.comparingByKey())
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_GATEWAY, "사용 가능한 기상 예보가 없습니다."));

        Map<String, String> values = selected.getValue();
        double temperature = number(values.get("T1H"));
        double windSpeed = number(values.get("WSD"));
        int humidity = (int) number(values.get("REH"));
        int precipitationType = (int) number(values.get("PTY"));
        String condition = condition((int) number(values.get("SKY")), precipitationType);
        boolean suitable = precipitationType == 0 && windSpeed < 10;

        return new WeatherResponse(
            temperature,
            condition,
            windSpeed,
            humidity,
            suitable,
            suitable ? "작업 적합" : "기상 주의",
            selected.getKey().atZone(KST).toOffsetDateTime().toString()
        );
    }

    private double number(String value) {
        try {
            return value == null ? 0 : Double.parseDouble(value);
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private String condition(int sky, int precipitationType) {
        return switch (precipitationType) {
            case 1 -> "비";
            case 2 -> "비·눈";
            case 3 -> "눈";
            case 5 -> "빗방울";
            case 6 -> "빗방울·눈날림";
            case 7 -> "눈날림";
            default -> switch (sky) {
                case 3 -> "구름 많음";
                case 4 -> "흐림";
                default -> "맑음";
            };
        };
    }

    public record WeatherResponse(
        double temperature,
        String condition,
        double windSpeed,
        int humidity,
        boolean workSuitable,
        String workStatus,
        String observedAt
    ) {
    }

    private record CachedWeather(LocalDateTime cachedAt, WeatherResponse weather) {
    }
}
