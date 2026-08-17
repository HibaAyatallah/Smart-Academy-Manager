from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
# Same-origin /api requests do not need CORS. Keep this empty unless a separate,
# explicitly trusted frontend origin is introduced.
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

LOGGING.setdefault("formatters", {})["production"] = {  # noqa: F405
    "format": "{asctime} {levelname} {name} {message}",
    "style": "{",
}
LOGGING["handlers"]["production_file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": env("DJANGO_LOG_FILE", default=str(BASE_DIR / "logs" / "django.log")),  # noqa: F405
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 5,
    "formatter": "production",
    "delay": True,
}
LOGGING["root"] = {"handlers": ["console", "production_file"], "level": "WARNING"}  # noqa: F405
LOGGING["loggers"]["apps.notifications"]["handlers"] = ["console", "production_file"]  # noqa: F405
