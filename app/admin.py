from django.contrib import admin

from .models import ChatUser, Message



@admin.register(ChatUser)
class ChatUserAdmin(admin.ModelAdmin):
	list_display = ("id", "fb_id", "username", "visit", "created_at")
	search_fields = ("fb_id", "username")
	list_filter = ("created_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ("id", "sender", "role", "created_at")
	search_fields = ("content", "sender__fb_id", "sender__username")
	list_filter = ("role", "created_at")