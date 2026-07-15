import shutil
import tempfile
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole

from .choices import (
    ApplicationDocumentType,
    ApplicationStatus,
    ApplicationType,
    StudyLevel,
)
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatusHistory,
    CandidateProfile,
    EmployeeProfile,
    InternProfile,
    Interview,
)

User = get_user_model()
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RecruitmentAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Throttle state is stored outside the test database. Reset it so a
        # public submission made by one test cannot rate-limit another test.
        cache.clear()
        self.hr = User.objects.create_user(
            email="hr@example.com",
            password="StrongPass123!",
            role=UserRole.HR,
        )
        self.employee = User.objects.create_user(
            email="employee@example.com",
            password="StrongPass123!",
            role=UserRole.EMPLOYEE,
        )

    def test_public_application_creation_creates_candidate_account_and_document(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(email="candidate@example.com"),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="candidate@example.com")
        self.assertEqual(user.role, UserRole.CANDIDATE)
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(Application.objects.count(), 1)
        application = Application.objects.first()
        self.assertEqual(application.documents.count(), 3)
        self.assertEqual(application.candidate_profile.study_field, "Developpement logiciel")
        self.assertNotIn("password", response.data)
        self.assertNotIn("file", response.data["documents"][0])
        self.assertIn("download_url", response.data["documents"][0])

    def test_candidate_can_access_only_own_application(self):
        own_application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=own_application.candidate)

        response = self.client.get(f"/api/applications/{own_application.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], own_application.pk)
        self.assertNotIn("password", response.data)

    def test_candidate_cannot_access_other_candidate_application(self):
        own_application = self.create_application("candidate@example.com")
        other_application = self.create_application("other@example.com")
        self.client.force_authenticate(user=own_application.candidate)

        response = self.client.get(f"/api/applications/{other_application.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_hr_can_list_and_filter_applications(self):
        self.create_application("candidate@example.com", ApplicationType.PFA_INTERNSHIP)
        self.create_application("hire@example.com", ApplicationType.HIRING)
        self.client.force_authenticate(user=self.hr)

        response = self.client.get(
            "/api/applications/",
            {"application_type": ApplicationType.HIRING},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["application_type"], ApplicationType.HIRING)

    def test_super_admin_can_list_paginated_applications(self):
        super_admin = User.objects.create_user(
            email="superadmin@example.com",
            password="StrongPass123!",
            role=UserRole.SUPER_ADMIN,
        )
        self.create_application("candidate@example.com", ApplicationType.PFA_INTERNSHIP)
        self.client.force_authenticate(user=super_admin)

        response = self.client.get("/api/applications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"][0]["application_type"], ApplicationType.PFA_INTERNSHIP)

    def test_application_list_returns_the_requested_drf_page(self):
        for index in range(21):
            self.create_application(f"candidate-{index}@example.com")
        self.client.force_authenticate(user=self.hr)

        response = self.client.get("/api/applications/", {"page": 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 21)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["previous"])

    def test_candidate_mine_endpoint_returns_paginated_own_applications(self):
        own_application = self.create_application("candidate@example.com")
        self.create_application("other@example.com")
        self.client.force_authenticate(user=own_application.candidate)

        response = self.client.get("/api/applications/mine/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"][0]["id"], own_application.pk)
        self.assertNotIn("password", response.data["results"][0])

    def test_document_urls_use_the_protected_download_endpoint(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(email="candidate@example.com"),
            format="multipart",
        )

        download_url = response.data["documents"][0]["download_url"]

        self.assertIn("/api/application-documents/", download_url)
        self.assertTrue(download_url.endswith("/download/"))
        self.assertNotIn("/media/", download_url)
        self.assertNotIn("\\", download_url)

    def test_other_roles_cannot_access_application_module(self):
        self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.employee)

        response = self.client.get("/api/applications/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_candidate_owner_can_download_own_document(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=application.candidate)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_candidate_cannot_download_other_candidate_document(self):
        application = self.create_application("candidate@example.com")
        other_application = self.create_application("other@example.com")
        document = self.create_document(other_application)
        self.client.force_authenticate(user=application.candidate)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_hr_can_download_candidate_document(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=self.hr)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_super_admin_can_download_candidate_document(self):
        super_admin = User.objects.create_user(
            email="superadmin-document@example.com",
            password="StrongPass123!",
            role=UserRole.SUPER_ADMIN,
        )
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=super_admin)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_download_candidate_document(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=self.employee)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_view_document_from_django_admin(self):
        super_admin = User.objects.create_user(
            email="admin-document@example.com",
            password="StrongPass123!",
            role=UserRole.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=None)
        self.client.force_login(super_admin)

        response = self.client.get(
            reverse("admin:recruitment_applicationdocument_view", args=[document.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_candidate_profile_admin_groups_recruitment_dossier(self):
        super_admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=UserRole.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=ApplicationStatus.SUBMITTED,
            to_status=ApplicationStatus.UNDER_REVIEW,
            changed_by=self.hr,
            comment="Dossier analyse.",
        )
        Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() + timedelta(days=1),
            location="Salle RH",
            created_by=self.hr,
        )
        self.client.force_login(super_admin)

        response = self.client.get(
            reverse(
                "admin:recruitment_candidateprofile_change",
                args=[application.candidate_profile_id],
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Informations personnelles")
        self.assertContains(response, "Documents securises")
        self.assertContains(response, "Historique des statuts")
        self.assertContains(response, "Entretiens")
        self.assertContains(response, "Voir le document")
        self.assertContains(
            response,
            reverse("admin:recruitment_application_change", args=[application.pk]),
        )
        self.assertContains(
            response,
            reverse("admin:recruitment_applicationdocument_view", args=[document.pk]),
        )

    def test_documents_and_status_history_are_hidden_from_admin_menu(self):
        super_admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=UserRole.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        request = RequestFactory().get("/admin/")
        request.user = super_admin

        document_admin = admin.site._registry[ApplicationDocument]
        history_admin = admin.site._registry[ApplicationStatusHistory]

        self.assertFalse(document_admin.has_module_permission(request))
        self.assertFalse(history_admin.has_module_permission(request))

    def test_hr_can_change_application_status(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.hr)

        response = self.client.post(f"/api/applications/{application.pk}/preselect/", {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.PRESELECTED)
        self.assertEqual(application.status_history.first().to_status, ApplicationStatus.PRESELECTED)

    def test_hr_can_execute_the_complete_application_workflow(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.hr)

        self.assertEqual(
            self.client.post(f"/api/applications/{application.pk}/mark-under-review/", {}).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/applications/{application.pk}/preselect/", {}).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                f"/api/applications/{application.pk}/schedule-interview/",
                {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/applications/{application.pk}/complete-interview/", {}).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/applications/{application.pk}/accept/", {}).status_code,
            status.HTTP_200_OK,
        )

        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.ACCEPTED)
        self.assertEqual(application.interviews.count(), 1)
        self.assertEqual(application.status_history.count(), 5)

    def test_invalid_schedule_does_not_create_an_interview(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.hr)

        response = self.client.post(
            f"/api/applications/{application.pk}/schedule-interview/",
            {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.SUBMITTED)
        self.assertEqual(application.interviews.count(), 0)

    def test_final_application_rejects_an_incoherent_transition(self):
        application = self.create_application(
            "candidate@example.com",
            status_value=ApplicationStatus.PRESELECTED,
        )
        self.client.force_authenticate(user=self.hr)
        self.client.post(f"/api/applications/{application.pk}/accept/", {})

        response = self.client.post(
            f"/api/applications/{application.pk}/reject/",
            {"reason": "Décision modifiée."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Transition invalide", str(response.data))

    def test_accepting_internship_transforms_candidate_into_intern(self):
        application = self.create_application(
            "candidate@example.com",
            ApplicationType.PFE_INTERNSHIP,
            status_value=ApplicationStatus.PRESELECTED,
        )
        self.client.force_authenticate(user=self.hr)

        response = self.client.post(f"/api/applications/{application.pk}/accept/", {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.INTERN)
        self.assertTrue(InternProfile.objects.filter(user=application.candidate).exists())

    def test_accepting_hiring_transforms_candidate_into_employee(self):
        application = self.create_application(
            "candidate@example.com",
            ApplicationType.HIRING,
            status_value=ApplicationStatus.PRESELECTED,
        )
        self.client.force_authenticate(user=self.hr)

        response = self.client.post(f"/api/applications/{application.pk}/accept/", {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.EMPLOYEE)
        self.assertTrue(EmployeeProfile.objects.filter(user=application.candidate).exists())

    def test_rejecting_application_disables_candidate_account(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.hr)

        response = self.client.post(
            f"/api/applications/{application.pk}/reject/",
            {"reason": "Profil non retenu."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        application.candidate.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.REJECTED)
        self.assertFalse(application.candidate.is_active)

    def test_invalid_file_extension_is_rejected(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(
                email="candidate@example.com",
                cv=SimpleUploadedFile(
                    "cv.exe",
                    b"invalid",
                    content_type="application/octet-stream",
                ),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="candidate@example.com").exists())

    def test_invalid_file_mime_type_is_rejected(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(
                email="candidate@example.com",
                cv=SimpleUploadedFile(
                    "cv.pdf",
                    b"not a real pdf",
                    content_type="text/plain",
                ),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv", response.data)

    def test_invalid_file_content_is_rejected(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(
                email="candidate@example.com",
                cv=SimpleUploadedFile(
                    "cv.pdf",
                    b"not a real pdf",
                    content_type="application/pdf",
                ),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv", response.data)

    @override_settings(RECRUITMENT_MAX_UPLOAD_SIZE_MB=1)
    def test_file_size_limit_is_enforced(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(
                email="candidate@example.com",
                cv=SimpleUploadedFile(
                    "cv.pdf",
                    b"x" * (1024 * 1024 + 1),
                    content_type="application/pdf",
                ),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv", response.data)

    @override_settings(RECRUITMENT_PHOTO_MAX_UPLOAD_SIZE_MB=1)
    def test_photo_size_limit_is_enforced(self):
        response = self.client.post(
            "/api/applications/public-submit/",
            self.public_application_payload(
                email="candidate@example.com",
                personal_photo=SimpleUploadedFile(
                    "photo.jpg",
                    b"\xff\xd8\xff" + b"x" * (1024 * 1024 + 1),
                    content_type="image/jpeg",
                ),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("personal_photo", response.data)

    def test_missing_required_cv_is_rejected(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload.pop("cv")

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv", response.data)

    def test_missing_required_cover_letter_is_rejected(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload.pop("cover_letter")

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cover_letter", response.data)

    def test_missing_required_personal_photo_is_rejected(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload.pop("personal_photo")

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("personal_photo", response.data)
        self.assertFalse(User.objects.filter(email="candidate@example.com").exists())

    def test_missing_required_text_field_is_rejected(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload["phone_number"] = ""

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_other_study_level_requires_precision(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload["study_level"] = StudyLevel.OTHER

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("study_level_other", response.data)

    def test_other_study_level_with_precision_is_accepted(self):
        payload = self.public_application_payload(email="candidate@example.com")
        payload["study_level"] = StudyLevel.OTHER
        payload["study_level_other"] = "Formation professionnelle"

        response = self.client.post(
            "/api/applications/public-submit/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = Application.objects.get().candidate_profile
        self.assertEqual(profile.study_level, StudyLevel.OTHER)
        self.assertEqual(profile.study_level_other, "Formation professionnelle")

    def public_application_payload(self, email, cv=None, cover_letter=None, personal_photo=None):
        return {
            "email": email,
            "password": "StrongPass123!",
            "first_name": "Jane",
            "last_name": "Candidate",
            "phone_number": "+212600000000",
            "current_school": "Smart University",
            "study_level": StudyLevel.MASTER,
            "study_field": "Developpement logiciel",
            "application_type": ApplicationType.PFA_INTERNSHIP,
            "motivation_message": "Je souhaite rejoindre Smart Academy.",
            "cv": cv
            or SimpleUploadedFile(
                "cv.pdf",
                b"%PDF-1.4 fake pdf",
                content_type="application/pdf",
            ),
            "cover_letter": cover_letter
            or SimpleUploadedFile(
                "lettre.pdf",
                b"%PDF-1.4 fake cover letter",
                content_type="application/pdf",
            ),
            "personal_photo": personal_photo
            or SimpleUploadedFile(
                "photo.jpg",
                b"\xff\xd8\xff fake image",
                content_type="image/jpeg",
            ),
        }

    def create_application(
        self,
        email,
        application_type=ApplicationType.PFA_INTERNSHIP,
        status_value=ApplicationStatus.SUBMITTED,
    ):
        user = User.objects.create_user(
            email=email,
            password="StrongPass123!",
            first_name="Jane",
            last_name="Candidate",
            role=UserRole.CANDIDATE,
        )
        profile = CandidateProfile.objects.create(
            user=user,
            phone_number="+212600000000",
            current_school="Smart University",
            study_level=StudyLevel.MASTER,
            study_field="Developpement logiciel",
        )
        return Application.objects.create(
            candidate_profile=profile,
            application_type=application_type,
            status=status_value,
        )

    def create_document(
        self,
        application,
        document_type=ApplicationDocumentType.CV,
        name="cv.pdf",
        content=b"%PDF-1.4 fake pdf",
        content_type="application/pdf",
    ):
        uploaded_file = SimpleUploadedFile(
            name,
            content,
            content_type=content_type,
        )
        return ApplicationDocument.objects.create(
            application=application,
            document_type=document_type,
            file=uploaded_file,
            original_name=name,
            content_type=content_type,
            size=uploaded_file.size,
            uploaded_by=application.candidate,
        )
