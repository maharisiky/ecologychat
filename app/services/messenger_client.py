import os

import requests


class MessengerClient:
    def __init__(self):
        self.page_access_token = os.getenv("PAGE_ACCESS_TOKEN", "")
        self.messaging_endpoint = os.getenv("MESSAGING_ENDPOINT", "")
        self.page_url = f"{self.messaging_endpoint}?access_token={self.page_access_token}"

    def send_message(self, recipient_id, message_text):
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text},
        }
        self._post(self.messaging_endpoint, params={"access_token": self.page_access_token}, json=payload)

    def send_action(self, recipient_id, action):
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": action,
        }
        self._post(self.page_url, json=payload)

    def _post(self, url, **kwargs):
        headers = {"Content-Type": "application/json"}
        return requests.post(url, headers=headers, timeout=10, **kwargs)