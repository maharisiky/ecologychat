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
            # if not quick reply : generate response with IA
            if 'quick_reply' not in message:
                print("Sending response message")
                print("Generating response message")
                response_message = self.ia.ask_gemini(sender_id, message)
                print(f"Response message: {response_message}")
            else:
                payload = message.get('quick_reply', {}).get('payload')
                print(f"Payload: {payload}")

                # Récupérer la réponse depuis la base de données
                try:
                    quick_reply = QuickReply.objects.get(payload=payload, is_active=True)
                    response_message = quick_reply.response_text
                except QuickReply.DoesNotExist:
                    response_message = "Desole, je n'ai pas compris votre demande. Veuillez reessayer."
                except Exception as e:
                    logger.exception("Erreur lors de la recuperation de la quick reply: %s", e)
                    response_message = "Desole, une erreur est survenue. Veuillez reessayer plus tard."

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

        # Récupérer les quick replies depuis la base de données
        quick_replies = []
        try:
            from app.models import QuickReply
            qr_objects = QuickReply.objects.filter(is_active=True)
            quick_replies = [
                {"content_type": "text", "title": qr.title, "payload": qr.payload}
                for qr in qr_objects
            ]
        except Exception as e:
            # Fallback vers les quick replies codées en dur en cas d'erreur
            print(f"Erreur lors de la récupération des quick replies: {e}")
            quick_replies = [
                {"content_type": "text", "title": "À propos", "payload": "ABOUT"},
                {"content_type": "text", "title": "Savoir-faire", "payload": "SKILLS"},
                {"content_type": "text", "title": "Événements", "payload": "EVENTS"},
                {"content_type": "text", "title": "Challenges", "payload": "CHALLENGES"},
                {"content_type": "text", "title": "Quizz", "payload": "QUIZ"}
            ]


        data = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text, 
                "quick_replies": quick_replies
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