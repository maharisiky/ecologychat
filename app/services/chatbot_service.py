import logging
import os
import re
from pathlib import Path

from django.conf import settings

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None

from app.infrastructure.groq.text_generation_repository import GroqTextGenerationRepository
from app.models import ChatUser, Message, MessageRole

logger = logging.getLogger(__name__)


class ChatbotService:
    def __init__(self):
        self.primary_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.provider = getattr(settings, "IA_PROVIDER", "gemini")
        self.groq_repository = GroqTextGenerationRepository()

    def ask(self, sender, message, save=True):
        if self.provider == "groq":
            return self.ask_groq(sender, message, save=save)
        return self.ask_gemini(sender, message, save=save)

    def ask_gemini(self, sender, message, save=True):
        if genai is None:
            raise RuntimeError("google-generativeai is not installed")

        user = self._get_user(sender)
        message_text = self._extract_message_text(message)

        if save:
            Message.objects.create(sender=user, role=MessageRole.USER, content=message_text)

        history = Message.objects.filter(sender=user).order_by("-created_at")[:20]
        messages = [
            {"role": self._gemini_role(message_item.role), "parts": [message_item.content]}
            for message_item in reversed(history)
        ]
        messages.append({"role": "user", "parts": [self.get_prompt()]})

        api_keys = self._get_api_key_candidates()
        if not api_keys:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not configured")

        model_candidates = self.build_model_candidates(self.primary_model)
        last_error = None

        for api_key in api_keys:
            genai.configure(api_key=api_key)
            for model_name in model_candidates:
                try:
                    model = genai.GenerativeModel(model_name)
                    chat = model.start_chat(history=messages)
                    response = chat.send_message(message_text)
                    reply_text = (getattr(response, "text", "") or "").strip()
                    if not reply_text:
                        raise RuntimeError("Gemini API returned empty text content")

                    if save:
                        Message.objects.create(sender=user, role=MessageRole.ASSISTANT, content=reply_text)

                    return self.clean_text(reply_text)
                except Exception as exc:  # pragma: no cover - external API
                    last_error = exc
                    error_message = str(exc)
                    logger.warning("Gemini call failed with model=%s: %s", model_name, error_message)

                    if self._is_model_retryable_error(error_message):
                        continue

                    if self._is_key_retryable_error(error_message):
                        break

                    raise

        if last_error is None:
            raise RuntimeError("Gemini API request failed: no API key or model candidate available")
        raise last_error

    def ask_groq(self, sender, message, save=True):
        user = self._get_user(sender)
        message_text = self._extract_message_text(message)

        if save:
            Message.objects.create(sender=user, role=MessageRole.USER, content=message_text)

        history = Message.objects.filter(sender=user).order_by("-created_at")[:20]
        messages = [
            {"role": self._groq_role(message_item.role), "content": message_item.content}
            for message_item in reversed(history)
        ]

        assistant_text = self.groq_repository.generate_chat_completion(
            messages,
            system_prompt=self.get_prompt(),
        )
        if save:
            Message.objects.create(sender=user, role=MessageRole.ASSISTANT, content=assistant_text)
        return self.clean_text(assistant_text)

    def get_prompt(self):
        prompt_file = Path(settings.BASE_DIR) / "static" / "prompt.txt"
        if not prompt_file.exists():
            logger.warning("Prompt file not found at %s", prompt_file)
            return ""
        return prompt_file.read_text(encoding="utf-8")

    @staticmethod
    def clean_text(text):
        # Nettoyer markdown et caracteres qui bloquent l'affichage Messenger
        cleaned = (text or "").replace("**", "")
        cleaned = cleaned.replace("\u202f", " ").replace("\u00a0", " ")
        # Normaliser les espaces multiples
        cleaned = re.sub(r" {2,}", " ", cleaned)
        return cleaned.strip()

    def build_model_candidates(self, primary_model):
        normalized_primary = self._normalize_model_name(primary_model)
        env_candidates = [self._normalize_model_name(item) for item in getattr(settings, "GEMINI_MODEL_FALLBACKS", [])]
        candidates = [primary_model, normalized_primary, *env_candidates]

        unique = []
        for candidate in candidates:
            value = self._normalize_model_name(candidate)
            if value and value not in unique:
                unique.append(value)

        max_models = max(1, int(getattr(settings, "GEMINI_MODEL_SWITCH_MAX_MODELS", 3) or 3))
        return unique[:max_models]

    @staticmethod
    def _get_api_key_candidates():
        candidates = [
            os.getenv("GEMINI_API_KEY", "").strip(),
            os.getenv("GEMINI_API_KEY_FALLBACK", "").strip(),
            os.getenv("GOOGLE_API_KEY", "").strip(),
            os.getenv("GOOGLE_API_KEY_FALLBACK", "").strip(),
        ]
        unique = []
        for candidate in candidates:
            if candidate and candidate not in unique:
                unique.append(candidate)
        return unique

    @staticmethod
    def _normalize_model_name(model_name):
        normalized = (model_name or "").strip().strip('"').strip("'")
        normalized = normalized.replace('\\"', "").replace("\\", "")
        normalized = re.sub(r"^models/", "", normalized)
        normalized = re.sub(r"gemini-(\d+)-(\d+)-", r"gemini-\1.\2-", normalized)
        return normalized

    @staticmethod
    def _is_model_retryable_error(message):
        lower_message = (message or "").lower()
        retry_tokens = ["429", "resource_exhausted", "quota", "rate limit", "404", "not_found"]
        return any(token in lower_message for token in retry_tokens)

    @staticmethod
    def _is_key_retryable_error(message):
        lower_message = (message or "").lower()
        retry_tokens = ["401", "403", "permission_denied", "api key", "unauthenticated"]
        return any(token in lower_message for token in retry_tokens)

    @staticmethod
    def _extract_message_text(message):
        return message.get("text", "") if isinstance(message, dict) else str(message)

    @staticmethod
    def _gemini_role(role):
        return "model" if role == MessageRole.ASSISTANT else "user"

    @staticmethod
    def _groq_role(role):
        return "assistant" if role == MessageRole.ASSISTANT else "user"

    @staticmethod
    def _get_user(sender):
        user, _ = ChatUser.objects.get_or_create(fb_id=sender)
        return user