import logging
import os

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.users import ChatUserViewSet
from app.services.chatbot_service import ChatbotService
from app.services.messenger_client import MessengerClient

logger = logging.getLogger(__name__)


class UserViewSet(ChatUserViewSet):
    pass


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv()
        self.verify_token = os.getenv("VERIFY_TOKEN")
        self.ia = ChatbotService()
        self.messenger_client = MessengerClient()

    def get(self, request):
        mode = request.query_params.get("hub.mode") or request.query_params.get("hub_mode")
        challenge = request.query_params.get("hub.challenge") or request.query_params.get("hub_challenge")
        verify_token = request.query_params.get("hub.verify_token") or request.query_params.get("hub_verify_token")

        if mode == "subscribe" and verify_token == self.verify_token and challenge:
            return HttpResponse(challenge, content_type="text/plain", status=status.HTTP_200_OK)

        logger.warning(
            "Webhook verification failed (mode=%s, token_match=%s, challenge_present=%s)",
            mode,
            verify_token == self.verify_token,
            bool(challenge),
        )
        return HttpResponse("Invalid verification request", status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        data = request.data or {}
        entries = data.get("entry", [])

        if not entries:
            logger.warning("Webhook payload missing entry: %s", data)
            return Response("ok", status=status.HTTP_200_OK)

        messaging_events = entries[0].get("messaging", [])
        if not messaging_events:
            logger.info("Webhook event without messaging block: %s", entries[0])
            return Response("ok", status=status.HTTP_200_OK)

        messaging = messaging_events[0]
        sender_id = messaging.get("sender", {}).get("id")
        if not sender_id:
            logger.warning("Webhook event without sender id: %s", messaging)
            return Response("ok", status=status.HTTP_200_OK)

        if "message" not in messaging:
            logger.info("Non-message event received: %s", messaging.keys())
            return Response("ok", status=status.HTTP_200_OK)

        message = messaging.get("message", {})
        self.messenger_client.send_action(sender_id, "mark_seen")
        self.messenger_client.send_action(sender_id, "typing_on")

        try:
            if "text" not in message:
                non_text_message = (
                    "Je suis desole, je ne peux pas traiter ce type de message pour le moment.\n"
                    "Merci d'envoyer un message texte."
                )
                self.messenger_client.send_message(sender_id, non_text_message)
                return Response("ok", status=status.HTTP_200_OK)

            response_message = self.ia.ask(sender_id, message)
            self.messenger_client.send_message(sender_id, response_message)
        except Exception:
            logger.exception("Error while processing webhook message for sender_id=%s", sender_id)
            self.messenger_client.send_message(
                sender_id,
                "Desole, une erreur technique est survenue. Merci de reessayer dans quelques instants.",
            )
        finally:
            self.messenger_client.send_action(sender_id, "typing_off")

        return Response("ok", status=status.HTTP_200_OK)


def health_view(request):
    return JsonResponse({"status": "ok"})