from django.test import TestCase
from django.urls import reverse

from app.models import ChatUser, Message, MessageRole


class ModelSmokeTests(TestCase):
	def test_chat_user_string_representation(self):
		user = ChatUser.objects.create(fb_id=123456789)
		self.assertIn("123456789", str(user))

	def test_message_relation_uses_new_models(self):
		user = ChatUser.objects.create(fb_id=42)
		message = Message.objects.create(sender=user, role=MessageRole.USER, content="hello")
		self.assertEqual(message.sender, user)
		self.assertEqual(message.role, MessageRole.USER)


class HealthViewTests(TestCase):
	def test_health_check_returns_ok(self):
		response = self.client.get(reverse("health_check"))
		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(response.content, {"status": "ok"})