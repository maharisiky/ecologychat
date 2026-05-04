# Generated manually during architecture refactor.

from django.db import migrations, models
import django.db.models.deletion


def normalize_message_roles(apps, schema_editor):
    Message = apps.get_model("app", "Message")
    Message.objects.filter(role__iexact="user").update(role="user")
    Message.objects.filter(role__in=["bot", "chatbot", "assistant", "BOT", "CHATBOT", "ASSISTANT"]).update(
        role="assistant"
    )


def reverse_normalize_message_roles(apps, schema_editor):
    Message = apps.get_model("app", "Message")
    Message.objects.filter(role="assistant").update(role="CHATBOT")


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_messages"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="User",
            new_name="ChatUser",
        ),
        migrations.RenameModel(
            old_name="Messages",
            new_name="Message",
        ),
        migrations.AlterField(
            model_name="chatuser",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="chatuser",
            name="fb_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="chatuser",
            name="username",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="chatuser",
            name="visit",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="message",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="message",
            name="role",
            field=models.CharField(
                choices=[("user", "User"), ("assistant", "Assistant")],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="message",
            name="sender",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="app.chatuser",
            ),
        ),
        migrations.RunPython(normalize_message_roles, reverse_normalize_message_roles),
    ]