from django.apps import AppConfig


class UserConfig(AppConfig):
    name = "apps.user"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import apps.user.signals
