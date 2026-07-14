from django.db import models


class ApplicationType(models.TextChoices):
    PFA_INTERNSHIP = "PFA_INTERNSHIP", "Stage PFA"
    PFE_INTERNSHIP = "PFE_INTERNSHIP", "Stage PFE"
    HIRING = "HIRING", "Candidature pour embauche"


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Candidature deposee"
    UNDER_REVIEW = "UNDER_REVIEW", "En cours d'etude"
    PRESELECTED = "PRESELECTED", "Preselectionne"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED", "Entretien planifie"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED", "Entretien realise"
    ACCEPTED = "ACCEPTED", "Accepte"
    REJECTED = "REJECTED", "Refuse"
    CANCELLED = "CANCELLED", "Annule"


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
