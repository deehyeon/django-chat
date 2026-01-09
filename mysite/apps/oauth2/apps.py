from django.apps import AppConfig


class Oauth2Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.oauth2"

    def ready(self):
        import apps.oauth2.signals
