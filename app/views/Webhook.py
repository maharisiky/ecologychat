import os
import logging
from dotenv import load_dotenv
from django.http import response, HttpResponse, JsonResponse
from rest_framework import viewsets, status
from rest_framework.views import APIView
from app.serializers import *
from app.models import *
import requests
from rest_framework.response import Response
from bs4 import BeautifulSoup
import time
from app.views.IA import IA

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class WebhookView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv()
        # getting verify token from .env
        self.verify_token = os.getenv("VERIFY_TOKEN")
        self.page_access_token = os.getenv("PAGE_ACCESS_TOKEN")
        self.messaging_endpoint = os.getenv('MESSAGING_ENDPOINT')
        self.page_url = f"{self.messaging_endpoint}?access_token={self.page_access_token}"

        self.ia = IA()

    def get(self, request):
        mode = request.query_params.get('hub.mode') or request.query_params.get('hub_mode')
        challenge = request.query_params.get('hub.challenge') or request.query_params.get('hub_challenge')
        verify_token = request.query_params.get('hub.verify_token') or request.query_params.get('hub_verify_token')

        if mode == 'subscribe' and verify_token == self.verify_token and challenge:
            return HttpResponse(challenge, content_type='text/plain', status=status.HTTP_200_OK)

        logger.warning(
            "Webhook verification failed (mode=%s, token_match=%s, challenge_present=%s)",
            mode,
            verify_token == self.verify_token,
            bool(challenge),
        )
        return HttpResponse("Invalid verification request", status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        data = request.data or {}
        entries = data.get('entry', [])

        if not entries:
            logger.warning("Webhook payload missing entry: %s", data)
            return Response("ok", status=status.HTTP_200_OK)

        messaging_events = entries[0].get('messaging', [])
        if not messaging_events:
            logger.info("Webhook event without messaging block: %s", entries[0])
            return Response("ok", status=status.HTTP_200_OK)

        messaging = messaging_events[0]
        sender_id = messaging.get('sender', {}).get('id')
        if not sender_id:
            logger.warning("Webhook event without sender id: %s", messaging)
            return Response("ok", status=status.HTTP_200_OK)

        # Ignore non-message events (delivery/read/postback, etc.)
        if 'message' not in messaging:
            logger.info("Non-message event received: %s", messaging.keys())
            return Response("ok", status=status.HTTP_200_OK)

        message = messaging.get('message', {})
        self.actions(sender_id, 'mark_seen')
        self.actions(sender_id, 'typing_on')

        try:
            # if the message is not a text message
            if 'text' not in message:
                non_text_message = (
                    "Je suis desole, je ne peux pas traiter ce type de message pour le moment.\n"
                    "Merci d'envoyer un message texte."
                )
                self.send_message(sender_id, non_text_message)
                return Response("ok", status=status.HTTP_200_OK)

            # manage payload
            print("Sending response message")
            print("Generating response message")
            response_message = self.ia.ask(sender_id, message)

            self.send_message(sender_id, response_message)
        except Exception:
            logger.exception("Error while processing webhook message for sender_id=%s", sender_id)
            self.send_message(
                sender_id,
                "Desole, une erreur technique est survenue. Merci de reessayer dans quelques instants.",
            )
        finally:
            self.actions(sender_id, 'typing_off')

        return Response("ok", status=status.HTTP_200_OK)



    def send_message(self, recipient_id, message_text):
        params = {
            "access_token": self.page_access_token
        }
        headers = {
            "Content-Type": "application/json"
        }



        data = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text, 
            }
        }

        requests.post(
            self.messaging_endpoint,
            params=params,
            headers=headers,
            json=data
        )


    def actions(self,recipient_id, action):
        payload = {
            'recipient': {'id': recipient_id},
            'sender_action': action,
        }
        headers = {'Content-Type': 'application/json'}
        requests.post(self.page_url, headers=headers, json=payload)


def healthView(request):
    return JsonResponse({"status": "ok"})