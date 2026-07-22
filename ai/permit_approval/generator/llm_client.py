"""LLM 호출 래퍼 — 명세 §3·§6.3.

Google Gemini REST API를 `requests`로 직접 부른다. `google-genai` SDK를 쓰지
않는 이유는 두 가지다. (1) `retrieval/corpus_fetcher.py`가 이미 공공 API를
requests로 다루고 있어 결이 같다. (2) 우리가 쓰는 기능이 generateContent 하나뿐인데
의존성을 하나 더 늘릴 이유가 없다. 구조화 출력도 REST의 responseSchema로 된다.

이 모듈은 **문자열을 받아 문자열을 돌려줄 뿐** 판정 스키마를 모른다.
JSON 파싱과 인용 검증은 rag.py의 몫이다.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

from config_loader import load_config, resolve

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv 미설치 시 환경변수만 사용
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


SETUP_GUIDE = """
LLM 인증키({env_key})가 설정되지 않았습니다.

1) https://aistudio.google.com/apikey 에서 API 키 발급 (무료 티어 있음)
2) 이 디렉터리의 .env에 {env_key}=발급받은키 를 입력

키가 없어도 명세 §9의 1~4단계(스키마·합성데이터·룰엔진·검색)는 정상 동작합니다.
생성기는 설명 없이 룰엔진 판정만 돌려줍니다.
"""


class MissingCredential(RuntimeError):
    """인증키 부재. 조용히 실패하지 않고 안내와 함께 터뜨린다."""


class LLMError(RuntimeError):
    """호출 실패. rag.py가 잡아서 '설명 없는 판정'으로 폴백한다."""


# 명세 §5.2의 LLM 생성 필드 두 개. 이 스키마를 벗어난 키는 요구하지 않는다.
# verdict를 넣지 않는 것이 핵심이다 — 모델에게 판정할 자리를 주지 않는다.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reject_comment": {"type": "string"},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["reject_comment", "recommended_actions"],
}


class LLMClient(Protocol):
    """생성기가 필요로 하는 최소 계약.

    프로토콜로 둔 덕분에 테스트는 MockClient를, 운영은 GeminiClient를 쓰고
    나중에 다른 공급자로 갈아끼워도 rag.py는 그대로다.
    """

    def complete(self, system: str, user: str) -> str:
        """JSON 문자열을 돌려준다. 실패는 LLMError."""


@dataclass
class GeminiClient:
    """Gemini generateContent 호출기."""

    model: str
    endpoint: str
    api_key: str
    temperature: float = 0.2
    max_output_tokens: int = 4096
    thinking_level: str | None = None
    timeout_sec: float = 60.0
    max_retries: int = 3
    request_interval_sec: float = 0.0

    # 스로틀용 내부 상태. 생성자 인자가 아니다.
    _last_call: float = field(default=0.0, init=False, repr=False)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> GeminiClient:
        config = config or load_config()
        gen = config["generator"]
        load_dotenv(resolve(".env"))

        env_key = gen.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(env_key, "").strip()
        if not api_key:
            raise MissingCredential(SETUP_GUIDE.format(env_key=env_key))

        return cls(
            model=gen["llm_model"],
            endpoint=gen["endpoint"].rstrip("/"),
            api_key=api_key,
            temperature=gen.get("temperature", 0.2),
            max_output_tokens=gen.get("max_output_tokens", 4096),
            thinking_level=gen.get("thinking_level"),
            timeout_sec=gen.get("timeout_sec", 60),
            max_retries=gen.get("max_retries", 3),
            request_interval_sec=gen.get("request_interval_sec", 0.0),
        )

    @property
    def url(self) -> str:
        return f"{self.endpoint}/{self.model}:generateContent"

    def _throttle(self) -> None:
        """무료 티어 RPM 보호. 연속 호출 사이 간격을 벌린다."""
        if self.request_interval_sec <= 0:
            return
        wait = self.request_interval_sec - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)

    def complete(self, system: str, user: str) -> str:
        generation_config: dict[str, Any] = {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_output_tokens,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        }
        if self.thinking_level:
            generation_config["thinkingConfig"] = {"thinkingLevel": self.thinking_level}

        payload = {
            # systemInstruction으로 분리해 넣는다. 허가서 본문(사용자 데이터)과
            # 제약 조건(시스템 지시)이 같은 평면에 섞이면 인젝션 표면이 넓어진다.
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation_config,
        }
        # 키는 헤더로 보낸다. 쿼리스트링에 넣으면 프록시·서버 로그에 남는다.
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        last_error = ""
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                response = requests.post(
                    self.url, json=payload, headers=headers, timeout=self.timeout_sec
                )
            except requests.RequestException as exc:
                last_error = f"네트워크 오류: {exc}"
            else:
                self._last_call = time.monotonic()
                if response.status_code == 200:
                    return self._extract_text(response.json())
                # 4xx는 재시도해도 같다 (키 오류·잘못된 모델명 등). 즉시 포기.
                if response.status_code < 500 and response.status_code != 429:
                    raise LLMError(
                        f"Gemini {response.status_code}: {response.text[:300]}"
                    )
                last_error = f"Gemini {response.status_code}: {response.text[:200]}"

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s

        raise LLMError(f"{self.max_retries}회 시도 실패 — {last_error}")

    @staticmethod
    def _extract_text(body: dict[str, Any]) -> str:
        """응답 본문에서 텍스트를 꺼낸다.

        안전 필터에 걸리면 candidates가 비거나 parts가 없다. 그 경우를
        구분해 알려야 rag.py의 폴백 로그가 원인을 담을 수 있다.
        """
        candidates = body.get("candidates") or []
        if not candidates:
            reason = body.get("promptFeedback", {}).get("blockReason", "알 수 없음")
            raise LLMError(f"응답에 후보가 없다 (blockReason={reason})")

        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        finish = candidates[0].get("finishReason", "알 수 없음")

        # thinking 모델은 사고 토큰이 예산을 다 먹으면 본문을 중간에 끊는다.
        # 그냥 두면 rag.py에서 "JSON을 찾지 못했다"로만 보여 원인 추적이 어렵다.
        if finish == "MAX_TOKENS":
            raise LLMError(
                f"출력이 잘렸다 (finishReason=MAX_TOKENS, 받은 길이 {len(text)}자). "
                "config.yaml의 generator.max_output_tokens를 늘리거나 "
                "thinking_level을 낮출 것."
            )
        if not text.strip():
            raise LLMError(f"빈 응답 (finishReason={finish})")
        return text


@dataclass
class MockClient:
    """테스트용. 실제 호출 없이 정해진 응답을 돌려준다.

    인젝션 시나리오를 재현하려면 verdict를 바꾸려 드는 응답을 그대로 넣으면 된다.
    생성기가 그 필드를 무시하는지가 검증 대상이다.
    """

    response: str = json.dumps(
        {"reject_comment": "테스트 응답", "recommended_actions": []},
        ensure_ascii=False,
    )
    error: Exception | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        return self.response


def get_client(config: dict[str, Any] | None = None) -> LLMClient:
    """config의 provider에 맞는 클라이언트를 만든다."""
    config = config or load_config()
    provider = config["generator"].get("provider", "gemini")
    if provider == "gemini":
        return GeminiClient.from_config(config)
    raise ValueError(f"알 수 없는 provider: {provider}")
