from django.contrib.auth.models import AbstractUser
from django.db import models

from .choices import UserRole
from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.CANDIDATE,
    )
    contact_email = models.EmailField("email de contact", blank=True, null=True)
    phone_number = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=2, choices=[("fr", "Français"), ("en", "English"), ("ar", "العربية")], default="fr")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]
        indexes = [
            models.Index(fields=["email"], name="accounts_us_email_742a89_idx"),
            models.Index(fields=["role"], name="accounts_us_role_c1c50b_idx"),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return self.get_full_name().strip() or self.email


class AccountSecurityLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="account_security_logs")
    action = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
