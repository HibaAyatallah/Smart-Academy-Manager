from django.db import models


class ApplicationType(models.TextChoices):
    PFA_INTERNSHIP = "PFA_INTERNSHIP", "Stage PFA"
    PFE_INTERNSHIP = "PFE_INTERNSHIP", "Stage PFE"
    HIRING = "HIRING", "Candidature pour embauche"


class ApplicationStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Reçue"
    UNDER_REVIEW = "UNDER_REVIEW", "En cours d'étude"
    PRESELECTED = "PRESELECTED", "Présélectionné"
    INTERVIEW = "INTERVIEW", "Entretien"
    ACCEPTED = "ACCEPTED", "Accepté"
    REJECTED = "REJECTED", "Refusé"
    ARCHIVED = "ARCHIVED", "Archivé"

class OfferStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PUBLISHED = "PUBLISHED", "Publiée"
    CLOSED = "CLOSED", "Fermée"
    ARCHIVED = "ARCHIVED", "Archivée"


class ApplicationDocumentType(models.TextChoices):
    CV = "CV", "CV"
    COVER_LETTER = "COVER_LETTER", "Lettre de motivation"
    PERSONAL_PHOTO = "PERSONAL_PHOTO", "Photo personnelle"
    OTHER = "OTHER", "Autre piece"


class StudyLevel(models.TextChoices):
    FIRST_YEAR = "FIRST_YEAR", "1re annee"
    SECOND_YEAR = "SECOND_YEAR", "2e annee"
    THIRD_YEAR = "THIRD_YEAR", "3e annee"
    FOURTH_YEAR = "FOURTH_YEAR", "4e annee"
    FIFTH_YEAR = "FIFTH_YEAR", "5e annee"
    BACHELOR = "BACHELOR", "Licence"
    MASTER = "MASTER", "Master"
    ENGINEERING = "ENGINEERING", "Cycle ingenieur"
    DOCTORATE = "DOCTORATE", "Doctorat"
    OTHER = "OTHER", "Autre"


class InternshipStatus(models.TextChoices):
    UPCOMING = "UPCOMING", "À venir"
    ACTIVE = "ACTIVE", "En cours"
    SUSPENDED = "SUSPENDED", "Suspendu"
    COMPLETED = "COMPLETED", "Terminé"
    CANCELLED = "CANCELLED", "Annulé"


class InternDocumentType(models.TextChoices):
    CONVENTION = "CONVENTION", "Convention de stage"
    INSURANCE = "INSURANCE", "Assurance"
    SCHOOL_CERT = "SCHOOL_CERT", "Attestation de scolarité"
    NDA = "NDA", "Accord de confidentialité"
    OTHER = "OTHER", "Autre document"


class EvaluationType(models.TextChoices):
    INITIAL = "INITIAL", "Évaluation initiale"
    MIDTERM = "MIDTERM", "Évaluation à mi-parcours"
    FINAL = "FINAL", "Évaluation finale"
