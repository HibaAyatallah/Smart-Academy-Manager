from django.db import models


class ProjectStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planifié"
    ACTIVE = "ACTIVE", "En cours"
    ON_HOLD = "ON_HOLD", "En pause"
    COMPLETED = "COMPLETED", "Terminé"
    CANCELLED = "CANCELLED", "Annulé"


class DeliverableStatus(models.TextChoices):
    PENDING = "PENDING", "À faire"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    SUBMITTED = "SUBMITTED", "Soumis"
    APPROVED = "APPROVED", "Validé"
    REJECTED = "REJECTED", "À corriger"
