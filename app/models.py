from django.db import models


class ChatUser(models.Model):
    username = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fb_id = models.BigIntegerField(null=True, blank=True)
    visit = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.username or str(self.fb_id) or f"ChatUser #{self.pk}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class Message(models.Model):
    sender = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender_id}:{self.role}"