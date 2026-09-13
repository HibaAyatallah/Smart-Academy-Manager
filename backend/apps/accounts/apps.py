from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        # Register drf-spectacular extensions once Django has loaded the app.
        from . import schema  # noqa: F401
