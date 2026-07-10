from .base import *  # noqa: F403

DEBUG = env.bool("DJANGO_DEBUG", default=True)  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

