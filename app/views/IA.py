from app.models import *
from dotenv import load_dotenv
import os
import re
import google.generativeai as genai
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
]

class IA :
    def __init__(self):
        load_dotenv()
        self.primary_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def get_prompt(self):
        prompt_file = Path(__file__).resolve().parents[2] / 'static' / 'prompt.txt'
        if not prompt_file.exists():
            logger.warning("Prompt file not found at %s", prompt_file)
            return ""
        with prompt_file.open('r', encoding='utf-8') as file:
            return file.read()

    def ask_gemini(self, sender, message, save=True):
            # get or create user
            user, _ = User.objects.get_or_create(fb_id=sender)

            # extract text from message object
            message_text = message.get('text', '') if isinstance(message, dict) else str(message)

            # save new message
            if save:
                Messages.objects.create(sender=user, role='USER', content=message_text)

            # history messages
            history = Messages.objects.filter(sender=user).order_by('-created_at')[:20]
            role_map = {'user': 'user', 'chatbot': 'model'}
            messages = [
                {"role": role_map.get(msg.role.lower(), "user"), "parts": [msg.content]}
                for msg in reversed(history)
            ]

            messages.append({
                "role": "user",
                "parts": [self.get_prompt()]
            })

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
                        reply_text = (getattr(response, 'text', '') or '').strip()
                        if not reply_text:
                            raise RuntimeError("Gemini API returned empty text content")

                        if save:
                            Messages.objects.create(sender=user, role='CHATBOT', content=reply_text).save()

                        return self.clean_text(reply_text)
                    except Exception as exc:
                        last_error = exc
                        error_message = str(exc)
                        logger.warning(
                            "Gemini call failed with model=%s: %s",
                            model_name,
                            error_message,
                        )

                        if self._is_model_retryable_error(error_message):
                            continue

                        if self._is_key_retryable_error(error_message):
                            break

                        raise

            if last_error is None:
                raise RuntimeError("Gemini API request failed: no API key or model candidate available")
            raise last_error

    def clean_text(self, text):
        text = text.replace('**', '')
        # text = re.sub(r'(?<=\n)(\d+\.)', r'\n\1', text)
        return text

    def build_model_candidates(self, primary_model):
        normalized_primary = self._normalize_model_name(primary_model)
        configured_fallbacks = os.getenv("GEMINI_MODEL_FALLBACKS", "").strip()
        env_candidates = [item.strip() for item in configured_fallbacks.split(",") if item.strip()] if configured_fallbacks else []

        candidates = [primary_model, normalized_primary, *env_candidates, *_GEMINI_FALLBACK_MODELS]
        unique = []
        for candidate in candidates:
            value = self._normalize_model_name(candidate)
            if value and value not in unique:
                unique.append(value)

        try:
            max_models = max(1, int(os.getenv("GEMINI_MODEL_SWITCH_MAX_MODELS", "3") or "3"))
        except ValueError:
            max_models = 3

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
        normalized = normalized.replace('\\"', '').replace('\\', '')
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
