from django.apps import AppConfig


class EcologyChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        from .scheduler import scheduler

        if not scheduler.running:
            scheduler.start()