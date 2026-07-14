from django.db import models


class NeedType(models.TextChoices):
    HIRING = "HIRING", "Recrutement"
    INTERNSHIP = "INTERNSHIP", "Stage"
    FREELANCE = "FREELANCE", "Freelance"


class NeedRequiredLevel(models.TextChoices):
    JUNIOR = "JUNIOR", "Junior (0-2 ans)"
    MID = "MID", "Intermédiaire (3-5 ans)"
    SENIOR = "SENIOR", "Senior (5+ ans)"
    EXPERT = "EXPERT", "Expert"


class NeedPriority(models.TextChoices):
    LOW = "LOW", "Basse"
    MEDIUM = "MEDIUM", "Moyenne"
    HIGH = "HIGH", "Haute"
    CRITICAL = "CRITICAL", "Critique"


class NeedStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    OPEN = "OPEN", "Ouvert"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    FULFILLED = "FULFILLED", "Pourvu"
    CANCELLED = "CANCELLED", "Annulé"
