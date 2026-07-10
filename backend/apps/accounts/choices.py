from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super administrateur"
    HR = "HR", "RH"
    BU_MANAGER = "BU_MANAGER", "Manager de Business Unit"
    TRAINER_TUTOR = "TRAINER_TUTOR", "Formateur / Tuteur"
    EMPLOYEE = "EMPLOYEE", "Collaborateur"
    INTERN = "INTERN", "Stagiaire"
    CANDIDATE = "CANDIDATE", "Candidat"
    CLIENT = "CLIENT", "Client"

