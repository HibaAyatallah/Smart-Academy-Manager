from django.db import models


class NeedType(models.TextChoices):
    RECRUITMENT_INTERNSHIP = "RECRUITMENT_INTERNSHIP", "Recrutement / stagiaire"
    TRAINING = "TRAINING", "Formation"
    OTHER = "OTHER", "Autre"


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
    SUBMITTED = "SUBMITTED", "Soumis"
    CONFIRMED = "CONFIRMED", "Confirmé"
    REFUSED = "REFUSED", "Refusé"
    DRAFT = "DRAFT", "Brouillon"
    OPEN = "OPEN", "Ouvert"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    VALIDATED = "VALIDATED", "Validé"
    FULFILLED = "FULFILLED", "Pourvu"
    CANCELLED = "CANCELLED", "Annulé"


class TrainingAudience(models.TextChoices):
    ALL = "ALL", "Tous les collaborateurs de la BU"
    SPECIFIC = "SPECIFIC", "Collaborateurs spécifiques"
