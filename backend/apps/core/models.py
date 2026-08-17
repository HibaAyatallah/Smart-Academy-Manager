from django.db import models


class ContactMessageStatus(models.TextChoices):
    NEW = "NEW", "Nouveau"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    RESOLVED = "RESOLVED", "Traité"


class ContactMessage(models.Model):
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    request_type = models.CharField(max_length=80, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=20,
        choices=ContactMessageStatus.choices,
        default=ContactMessageStatus.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject} — {self.email}"
