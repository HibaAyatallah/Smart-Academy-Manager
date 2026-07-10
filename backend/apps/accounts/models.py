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
    phone_number = models.CharField(max_length=32, blank=True)
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
