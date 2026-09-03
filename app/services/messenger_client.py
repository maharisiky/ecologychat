import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

# Facebook limite a 2000 caracteres, on garde une marge
MESSENGER_LIMIT = 1800


class MessengerClient:
    def __init__(self):
        self.page_access_token = os.getenv("PAGE_ACCESS_TOKEN", "")
        self.messaging_endpoint = os.getenv("MESSAGING_ENDPOINT", "")
        self.page_url = f"{self.messaging_endpoint}?access_token={self.page_access_token}"

    def send_message(self, recipient_id, message_text):
        if not message_text or not message_text.strip():
            logger.warning("Attempted to send empty message to %s", recipient_id)
            return None

        # Nettoyer les espaces insécables fines qui posent probleme d'affichage
        cleaned = message_text.replace("\u202f", " ").replace("\u00a0", " ")

        chunks = self._split_message(cleaned, MESSENGER_LIMIT)
        last_response = None
        for idx, chunk in enumerate(chunks):
            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": chunk},
            }
            last_response = self._post(
                self.messaging_endpoint, params={"access_token": self.page_access_token}, json=payload
            )
            # Petit delai entre les chunks pour l'ordre d'affichage
            if idx < len(chunks) - 1:
                time.sleep(0.4)
        return last_response

    def send_action(self, recipient_id, action):
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": action,
        }
        return self._post(self.page_url, json=payload)

    def _post(self, url, **kwargs):
        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(url, headers=headers, timeout=10, **kwargs)
            if resp.status_code >= 400:
                logger.error(
                    "Facebook API error %s: %s | url=%s payload=%s",
                    resp.status_code,
                    resp.text[:600],
                    url,
                    str(kwargs.get("json", ""))[:400],
                )
            return resp
        except Exception:
            logger.exception("Facebook API request failed url=%s", url)
            raise

    @staticmethod
    def _split_message(text, limit):
        """Decoupe un texte long en chunks < limit en coupant aux sauts de ligne."""
        if len(text) <= limit:
            return [text]
        chunks = []
        remaining = text
        while len(remaining) > limit:
            # Cherche le dernier saut de ligne avant la limite
            cut = remaining.rfind("\n", 0, limit)
            if cut == -1:
                cut = remaining.rfind(" ", 0, limit)
            if cut == -1 or cut < limit * 0.5:
                cut = limit
            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks