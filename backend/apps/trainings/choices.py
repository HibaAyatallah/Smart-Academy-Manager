from django.db import models

class TrainingType(models.TextChoices):
    INTERNAL = "INTERNAL", "Interne"
    CLIENT = "CLIENT", "Client"
    TECHNICAL = "TECHNICAL", "Technique"
    SOFT_SKILLS = "SOFT_SKILLS", "Soft Skills"
    CERTIFICATION = "CERTIFICATION", "Certification"
    E_LEARNING = "E_LEARNING", "E-Learning"


class DeliveryMode(models.TextChoices):
    ON_SITE = "ON_SITE", "Présentiel"
    REMOTE = "REMOTE", "Distanciel"
    HYBRID = "HYBRID", "Hybride"
    E_LEARNING = "E_LEARNING", "E-Learning"


class TrainingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PUBLISHED = "PUBLISHED", "Publié"
    ARCHIVED = "ARCHIVED", "Archivé"


class SessionStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planifiée"
    OPEN = "OPEN", "Ouverte"
    FULL = "FULL", "Complète"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    COMPLETED = "COMPLETED", "Terminée"
    CANCELLED = "CANCELLED", "Annulée"


class EnrollmentStatus(models.TextChoices):
    PENDING_MANAGER = "PENDING_MANAGER", "En attente du manager"
    REJECTED_BY_MANAGER = "REJECTED_BY_MANAGER", "Refusé par le manager"
    PENDING_SUPER_ADMIN = "PENDING_SUPER_ADMIN", "En attente du Super Admin"
    REJECTED_BY_SUPER_ADMIN = "REJECTED_BY_SUPER_ADMIN", "Refusé par le Super Admin"
    APPROVED = "APPROVED", "Approuvée"
    ENROLLED = "ENROLLED", "Inscrit"
    COMPLETED = "COMPLETED", "Terminée"
    CANCELLED = "CANCELLED", "Annulée"
