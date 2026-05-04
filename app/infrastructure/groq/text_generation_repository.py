import os
from collections.abc import Iterator

import requests

GDP_SYSTEM_PROMPT = """You are an assistant that helps with ecology-related questions."""


class GroqTextGenerationRepository:
    def generate_chat_completion(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        model = self._resolve_model()
        return self._call_groq(messages=messages, model=model, system_prompt=system_prompt)

    def generate_chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> tuple[Iterator[str], str]:
        model = self._resolve_model()
        text = self._call_groq(messages=messages, model=model, system_prompt=system_prompt)

        def _iterator() -> Iterator[str]:
            if text:
                yield text

        return _iterator(), model

    def _resolve_model(self) -> str:
        raw_model = (
            os.getenv("GROQ_CHAT_MODEL", "").strip()
            or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        )
        return self._normalize_env_value(raw_model)

    @staticmethod
    def _normalize_env_value(value: str) -> str:
        return value.strip().strip('"').strip("'").replace("\\", "")

    @classmethod
    def _resolve_api_key(cls) -> str:
        return (
            cls._normalize_env_value(os.getenv("GROQ_API_KEY", ""))
            or cls._normalize_env_value(os.getenv("GROQ_KEY", ""))
        )

    @staticmethod
    def _build_messages(messages: list[dict[str, str]], system_prompt: str | None) -> list[dict[str, str]]:
        prompt = (system_prompt or "").strip() or GDP_SYSTEM_PROMPT
        return [{"role": "system", "content": prompt}, *messages]

    @classmethod
    def _call_groq(cls, *, messages: list[dict[str, str]], model: str, system_prompt: str | None = None) -> str:
        api_key = cls._resolve_api_key()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY (or GROQ_KEY) is not configured")

        endpoint = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "messages": cls._build_messages(messages, system_prompt),
                "temperature": float(os.getenv("GROQ_CHAT_TEMPERATURE", os.getenv("GROQ_TEMPERATURE", "0.2")) or "0.2"),
                "max_completion_tokens": int(
                    os.getenv("GROQ_CHAT_MAX_TOKENS", os.getenv("GROQ_MAX_TOKENS", "4096")) or "4096"
                ),
            },
            timeout=int(os.getenv("GROQ_CHAT_TIMEOUT_SECONDS", os.getenv("GROQ_TIMEOUT_SECONDS", "90")) or "90"),
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Groq API request failed ({response.status_code}): {response.text[:400]}")

        body = response.json()
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("Groq API response did not contain choices")

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message") if isinstance(first_choice, dict) else None
        text_payload = ""
        if isinstance(message, dict):
            text_payload = str(message.get("content", "")).strip()

        if not text_payload:
            raise RuntimeError("Groq API returned empty text content")

        return text_payload
