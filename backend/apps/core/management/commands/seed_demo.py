import os
from datetime import time, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.notifications.models import AuditLog, Notification, NotificationCategory
from apps.projects.choices import DeliverableStatus, ProjectStatus
from apps.projects.models import Project, ProjectAssignment, ProjectDeliverable
from apps.recruitment.choices import (
    ApplicationStatus,
    ApplicationType,
    InternshipStatus,
    OfferStatus,
    StudyLevel,
)
from apps.recruitment.models import (
    Application,
    ApplicationMatch,
    CandidateProfile,
    CVAnalysis,
    InternProfile,
    Offer,
)
from apps.trainings.choices import (
    DeliveryMode,
    EnrollmentStatus,
    SessionStatus,
    TrainingStatus,
    TrainingType,
)
from apps.trainings.models import (
    ClientProfile,
    SessionAttendance,
    Training,
    TrainingCertificate,
    TrainingEnrollment,
    TrainingSession,
)


class Command(BaseCommand):
    help = "Create or update a safe, repeatable demonstration dataset without deleting data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=os.environ.get("DEMO_PASSWORD"),
            help="Password for demo accounts (or set DEMO_PASSWORD).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Account-creation signals must not contact a real SMTP server while a
        # local/demo dataset is being assembled. This process exits after the
        # command, so the override cannot leak into the running application.
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        settings.EMAIL_RAISE_DELIVERY_ERRORS = False
        password = options["password"]
        if not password or len(password) < 12:
            raise CommandError("Provide --password or DEMO_PASSWORD with at least 12 characters.")

        users = {}
        definitions = {
            "admin": ("admin.demo@example.test", UserRole.SUPER_ADMIN, "Amine", "Admin"),
            "hr": ("rh.demo@example.test", UserRole.HR, "Salma", "RH"),
            "manager": ("manager.demo@example.test", UserRole.BU_MANAGER, "Youssef", "Manager"),
            "trainer": ("trainer.demo@example.test", UserRole.TRAINER_TUTOR, "Nadia", "Trainer"),
            "employee": ("collaborator.demo@example.test", UserRole.EMPLOYEE, "Karim", "Collaborator"),
            "intern": ("intern.demo@example.test", UserRole.INTERN, "Imane", "Intern"),
            "candidate": ("candidate.demo@example.test", UserRole.CANDIDATE, "Lina", "Candidate"),
            "client": ("client.demo@example.test", UserRole.CLIENT, "Omar", "Client"),
        }
        for key, (email, role, first_name, last_name) in definitions.items():
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True,
                    "is_staff": role == UserRole.SUPER_ADMIN,
                    "is_superuser": role == UserRole.SUPER_ADMIN,
                    "must_change_password": False,
                },
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            users[key] = user

        units = {}
        for code, description in {
            "NETSEC": "Cybersécurité et réseaux",
            "SYSTEM": "Systèmes et infrastructure",
            "SOFTWARE": "Ingénierie logicielle",
            "ACHAT": "Achats et fournisseurs",
        }.items():
            unit, _ = BusinessUnit.objects.update_or_create(
                code=code,
                defaults={"name": code.title(), "description": description, "is_active": True},
            )
            units[code] = unit
        software = units["SOFTWARE"]
        software.manager = users["manager"]
        software.save(update_fields=["manager"])
        for key, position in (("manager", "BU Manager"), ("employee", "Software Engineer"), ("intern", "Software Intern")):
            BusinessUnitMembership.objects.update_or_create(
                business_unit=software,
                user=users[key],
                is_active=True,
                defaults={"position": position},
            )

        candidate, _ = CandidateProfile.objects.update_or_create(
            user=users["candidate"],
            defaults={
                "phone_number": "+212600000001",
                "current_school": "École Démo Casablanca",
                "study_level": StudyLevel.ENGINEERING,
                "study_field": "Génie logiciel",
                "address": "Casablanca",
            },
        )
        offer, _ = Offer.objects.update_or_create(
            title="Stage PFE – API Django et Angular",
            business_unit=software,
            defaults={
                "description": "Contribuer à une plateforme de gestion académique.",
                "application_type": ApplicationType.PFE_INTERNSHIP,
                "required_skills": "Python, Django, REST API, Angular, MySQL",
                "required_level": StudyLevel.ENGINEERING,
                "number_of_positions": 2,
                "location": "Casablanca",
                "publication_date": timezone.localdate(),
                "application_deadline": timezone.localdate() + timedelta(days=30),
                "status": OfferStatus.PUBLISHED,
                "created_by": users["hr"],
            },
        )
        application, _ = Application.objects.update_or_create(
            candidate_profile=candidate,
            offer=offer,
            defaults={
                "application_type": ApplicationType.PFE_INTERNSHIP,
                "status": ApplicationStatus.PRESELECTED,
                "motivation_message": "Candidature fictive créée pour la démonstration.",
                "reviewed_by": users["hr"],
            },
        )
        CVAnalysis.objects.update_or_create(
            application=application,
            defaults={
                "skills": ["Python", "Django", "Angular", "MySQL", "REST API"],
                "experiences": [{"title": "Projet académique", "duration_months": 6}],
                "diplomas": ["Cycle ingénieur – Génie logiciel"],
                "contact_details": {"email": users["candidate"].email, "location": "Casablanca"},
                "full_name": users["candidate"].full_name,
                "email": users["candidate"].email,
                "phone": candidate.phone_number,
                "location": "Casablanca",
                "education": [{"degree": "Cycle ingénieur", "field": "Génie logiciel"}],
                "languages": ["Français", "Anglais"],
                "extraction_method": "DEMO_STRUCTURED",
                "source_sha256": "demo-seed-not-a-real-document",
                "extractor_version": "rules-v1",
                "human_validated": True,
                "validated_by": users["hr"],
                "validated_at": timezone.now(),
            },
        )
        ApplicationMatch.objects.update_or_create(
            application=application,
            offer=offer,
            defaults={
                "score": 86,
                "matched_skills": ["Python", "Django", "Angular", "MySQL", "REST API"],
                "missing_skills": [],
                "additional_skills": [],
                "score_breakdown": {"skills": 86},
                "candidate_summary": "Profil fictif bien aligné avec l’offre.",
                "explanation": "Score déterministe basé sur la correspondance des compétences.",
                "algorithm_version": "skills-v2",
                "human_decision": "APPROVED",
                "reviewed_by": users["hr"],
                "reviewed_at": timezone.now(),
            },
        )
        converted_candidate, _ = CandidateProfile.objects.update_or_create(
            user=users["intern"],
            defaults={
                "phone_number": "+212600000002",
                "current_school": "École Démo Casablanca",
                "study_level": StudyLevel.ENGINEERING,
                "study_field": "Génie logiciel",
                "address": "Casablanca",
            },
        )
        converted_application, _ = Application.objects.update_or_create(
            candidate_profile=converted_candidate,
            offer=offer,
            defaults={
                "application_type": ApplicationType.PFE_INTERNSHIP,
                "status": ApplicationStatus.ACCEPTED,
                "motivation_message": "Candidature fictive convertie en profil stagiaire.",
                "reviewed_by": users["hr"],
                "accepted_at": timezone.now(),
            },
        )
        InternProfile.objects.update_or_create(
            user=users["intern"],
            defaults={
                "source_application": converted_application,
                "school": "École Démo Casablanca",
                "specialization": "Génie logiciel",
                "internship_type": "PFE",
                "business_unit": software,
                "supervisor": users["manager"],
                "subject_title": "Portail de formation interne",
                "internship_start": timezone.localdate() - timedelta(days=30),
                "internship_end": timezone.localdate() + timedelta(days=90),
                "current_status": InternshipStatus.ACTIVE,
                "progress": 35,
            },
        )

        client, _ = ClientProfile.objects.update_or_create(
            user=users["client"], defaults={"company_name": "Atlas Demo SARL", "project_info": "Formation sécurisée fictive"}
        )
        training, _ = Training.objects.update_or_create(
            title="Django REST & Angular – Démonstration",
            defaults={
                "description": "Parcours technique fictif pour la démonstration.",
                "training_type": TrainingType.TECHNICAL,
                "category": "Software",
                "objectives": "Construire et sécuriser une API REST.",
                "prerequisites": "Bases Python et TypeScript",
                "duration": 16,
                "delivery_mode": DeliveryMode.HYBRID,
                "level": "Intermédiaire",
                "trainer": users["trainer"],
                "business_unit": software,
                "external_client": client,
                "project_name": "Smart Academy Demo",
                "status": TrainingStatus.PUBLISHED,
                "created_by": users["admin"],
            },
        )
        session, _ = TrainingSession.objects.update_or_create(
            training=training,
            start_date=timezone.localdate() + timedelta(days=7),
            defaults={
                "end_date": timezone.localdate() + timedelta(days=8),
                "start_time": time(9),
                "end_time": time(17),
                "location": "Salle Démo, Casablanca",
                "online_link": "https://example.test/demo-session",
                "trainer": users["trainer"],
                "maximum_participants": 20,
                "status": SessionStatus.OPEN,
                "external_client": client,
                "created_by": users["admin"],
            },
        )
        enrollment, _ = TrainingEnrollment.objects.update_or_create(
            user=users["employee"],
            session=session,
            defaults={
                "training": training,
                "status": EnrollmentStatus.COMPLETED,
                "final_status": EnrollmentStatus.COMPLETED,
                "manager_decision": EnrollmentStatus.PENDING_SUPER_ADMIN,
                "manager_decided_by": users["manager"],
                "manager_decided_at": timezone.now(),
                "super_admin_decision": EnrollmentStatus.APPROVED,
                "super_admin_decided_by": users["admin"],
                "super_admin_decided_at": timezone.now(),
            },
        )
        SessionAttendance.objects.update_or_create(
            enrollment=enrollment,
            date=session.start_date,
            defaults={
                "status": "PRESENT",
                "validated": True,
                "recorded_by": users["trainer"],
                "validated_by": users["trainer"],
                "validated_at": timezone.now(),
            },
        )
        certificate, created = TrainingCertificate.objects.get_or_create(
            enrollment=enrollment,
            defaults={"certificate_number": "SAM-DEMO-0001", "issued_by": users["admin"]},
        )
        if created or not certificate.file:
            certificate.file.save("sam-demo-certificate.txt", ContentFile(b"Smart Academy Manager demo certificate\n"), save=True)

        project, _ = Project.objects.update_or_create(
            title="Portail Smart Academy – Démonstration",
            defaults={
                "description": "Projet fictif illustrant affectations et livrables.",
                "business_unit": software,
                "supervisor": users["manager"],
                "start_date": timezone.localdate() - timedelta(days=14),
                "end_date": timezone.localdate() + timedelta(days=45),
                "status": ProjectStatus.ACTIVE,
                "progress": 40,
                "created_by": users["manager"],
            },
        )
        ProjectAssignment.objects.get_or_create(project=project, user=users["employee"])
        ProjectAssignment.objects.get_or_create(project=project, user=users["intern"])
        ProjectDeliverable.objects.update_or_create(
            project=project,
            title="Prototype API et interface",
            defaults={
                "description": "Livrable fictif de démonstration.",
                "due_date": timezone.localdate() + timedelta(days=14),
                "status": DeliverableStatus.IN_PROGRESS,
                "created_by": users["manager"],
                "updated_by": users["employee"],
            },
        )
        Notification.objects.update_or_create(
            recipient=users["employee"],
            title="Nouvelle affectation de démonstration",
            defaults={
                "category": NotificationCategory.ASSIGNMENT,
                "message": "Vous avez été affecté au projet de démonstration.",
                "link": f"/projects/{project.pk}",
                "target_type": "Project",
                "target_id": str(project.pk),
            },
        )
        AuditLog.objects.update_or_create(
            actor=users["admin"],
            action="DEMO_DATA_SEEDED",
            target_type="DemoDataset",
            target_id="smart-academy",
            defaults={
                "actor_email": users["admin"].email,
                "method": "COMMAND",
                "path": "manage.py seed_demo",
                "status_code": 200,
                "metadata": {"safe": True, "synthetic": True},
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo dataset is ready (8 synthetic accounts; existing data preserved)."))
