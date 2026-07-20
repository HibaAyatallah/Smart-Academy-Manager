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
    OfferStatus,
)
from .models import (
    Application,
    ApplicationDocument,
    ApplicationStatusHistory,
    CandidateProfile,
    EmployeeProfile,
    InternDocument,
    InternEvaluation,
    InternProfile,
    Interview,
    Offer,
)
from apps.business_units.models import BusinessUnit, BusinessUnitMembership

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
        self.super_admin = User.objects.create_superuser(
            email="superadmin@example.com",
            password="StrongPass123!",
        )
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

    def test_super_admin_can_list_and_filter_applications(self):
        self.create_application("candidate@example.com", ApplicationType.PFA_INTERNSHIP)
        self.create_application("hire@example.com", ApplicationType.HIRING)
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.get(
            "/api/applications/",
            {"application_type": ApplicationType.HIRING},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["application_type"], ApplicationType.HIRING)

    def test_super_admin_can_list_paginated_applications(self):
        self.create_application("candidate@example.com", ApplicationType.PFA_INTERNSHIP)
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.get("/api/applications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"][0]["application_type"], ApplicationType.PFA_INTERNSHIP)

    def test_application_list_returns_the_requested_drf_page(self):
        for index in range(21):
            self.create_application(f"candidate-{index}@example.com")
        self.client.force_authenticate(user=self.super_admin)

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
        
        # HR gets 403
        self.client.force_authenticate(user=self.hr)
        response_hr = self.client.get("/api/applications/")
        self.assertEqual(response_hr.status_code, status.HTTP_403_FORBIDDEN)
        
        # Employee gets 403
        self.client.force_authenticate(user=self.employee)
        response_emp = self.client.get("/api/applications/")
        self.assertEqual(response_emp.status_code, status.HTTP_403_FORBIDDEN)

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

    def test_super_admin_can_download_candidate_document(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.get(f"/api/application-documents/{document.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_and_hr_cannot_download_candidate_document(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(f"/api/application-documents/{document.pk}/download/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.hr)
        response = self.client.get(f"/api/application-documents/{document.pk}/download/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_view_document_from_django_admin(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        self.client.force_authenticate(user=None)
        self.client.force_login(self.super_admin)

        response = self.client.get(
            reverse("admin:recruitment_applicationdocument_view", args=[document.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_candidate_profile_admin_groups_recruitment_dossier(self):
        application = self.create_application("candidate@example.com")
        document = self.create_document(application)
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=ApplicationStatus.RECEIVED,
            to_status=ApplicationStatus.UNDER_REVIEW,
            changed_by=self.super_admin,
            comment="Dossier analyse.",
        )
        Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() + timedelta(days=1),
            location="Salle RH",
            created_by=self.super_admin,
        )
        self.client.force_login(self.super_admin)

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
        request = RequestFactory().get("/admin/")
        request.user = self.super_admin

        document_admin = admin.site._registry[ApplicationDocument]
        history_admin = admin.site._registry[ApplicationStatusHistory]

        self.assertFalse(document_admin.has_module_permission(request))
        self.assertFalse(history_admin.has_module_permission(request))

    def test_super_admin_can_change_application_status(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.post(f"/api/applications/{application.pk}/preselect/", {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.PRESELECTED)
        self.assertEqual(application.status_history.first().to_status, ApplicationStatus.PRESELECTED)

    def test_super_admin_can_execute_the_complete_application_workflow(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.super_admin)

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
                f"/api/applications/{application.pk}/mark-interview/",
                {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"/api/applications/{application.pk}/accept/", {}).status_code,
            status.HTTP_200_OK,
        )

        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.ACCEPTED)
        self.assertEqual(application.interviews.count(), 1)
        self.assertEqual(application.status_history.count(), 4)

    def test_hr_cannot_change_application_status(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.hr)

        # HR receives 403 for preselect
        response = self.client.post(f"/api/applications/{application.pk}/preselect/", {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # HR receives 403 for accept
        response_accept = self.client.post(f"/api/applications/{application.pk}/accept/", {})
        self.assertEqual(response_accept.status_code, status.HTTP_403_FORBIDDEN)
        
        # Status has not changed
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.RECEIVED)

    def test_invalid_schedule_does_not_create_an_interview(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.post(
            f"/api/applications/{application.pk}/mark-interview/",
            {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.RECEIVED)
        self.assertEqual(application.interviews.count(), 0)

    def test_final_application_rejects_an_incoherent_transition(self):
        application = self.create_application(
            "candidate@example.com",
            status_value=ApplicationStatus.PRESELECTED,
        )
        self.client.force_authenticate(user=self.super_admin)
        self.client.post(f"/api/applications/{application.pk}/accept/", {})

        response = self.client.post(
            f"/api/applications/{application.pk}/reject/",
            {"reason": "Décision modifiée."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Transition invalide", str(response.data))

    def test_accepting_application_does_not_auto_convert_candidate(self):
        application = self.create_application(
            "candidate@example.com",
            ApplicationType.PFE_INTERNSHIP,
            status_value=ApplicationStatus.PRESELECTED,
        )
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.post(f"/api/applications/{application.pk}/accept/", {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.CANDIDATE)
        self.assertFalse(InternProfile.objects.filter(user=application.candidate).exists())

    def test_convert_accepted_application_to_intern(self):
        application = self.create_application(
            "candidate@example.com",
            ApplicationType.PFE_INTERNSHIP,
            status_value=ApplicationStatus.ACCEPTED,
        )
        # We need a BU manager for the BU
        bu_manager = User.objects.create_user(
            email="manager@example.com",
            password="pass",
            role=UserRole.BU_MANAGER,
        )
        bu = BusinessUnit.objects.create(
            name="Tech", code="TECH", manager=bu_manager
        )
        self.client.force_authenticate(user=self.super_admin)

        payload = {
            "conversion_type": "INTERN",
            "business_unit": bu.id,
            "supervisor": self.employee.id,
        }
        response = self.client.post(f"/api/applications/{application.pk}/convert/", payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.INTERN)
        self.assertTrue(InternProfile.objects.filter(user=application.candidate).exists())
        self.assertTrue(BusinessUnitMembership.objects.filter(user=application.candidate, business_unit=bu).exists())

    def test_convert_accepted_application_to_employee(self):
        application = self.create_application(
            "candidate2@example.com",
            ApplicationType.HIRING,
            status_value=ApplicationStatus.ACCEPTED,
        )
        bu_manager = User.objects.create_user(
            email="manager2@example.com",
            password="pass",
            role=UserRole.BU_MANAGER,
        )
        bu = BusinessUnit.objects.create(
            name="HR Dept", code="HR", manager=bu_manager
        )
        self.client.force_authenticate(user=self.super_admin)

        payload = {
            "conversion_type": "EMPLOYEE",
            "business_unit": bu.id,
        }
        response = self.client.post(f"/api/applications/{application.pk}/convert/", payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.EMPLOYEE)
        self.assertTrue(EmployeeProfile.objects.filter(user=application.candidate).exists())
        self.assertTrue(BusinessUnitMembership.objects.filter(user=application.candidate, business_unit=bu).exists())

    def test_rejecting_application_disables_candidate_account(self):
        application = self.create_application("candidate@example.com")
        self.client.force_authenticate(user=self.super_admin)

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
        status_value=ApplicationStatus.RECEIVED,
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


class OfferTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.super_admin = User.objects.create_superuser(
            email="superadmin@example.com",
            password="StrongPass123!",
        )
        self.hr = User.objects.create_user(
            email="hr@example.com",
            password="StrongPass123!",
            role=UserRole.HR,
        )
        self.bu_manager = User.objects.create_user(
            email="bumanager@example.com",
            password="StrongPass123!",
            role=UserRole.BU_MANAGER,
        )
        self.candidate = User.objects.create_user(
            email="candidate@example.com",
            password="StrongPass123!",
            role=UserRole.CANDIDATE,
        )
        self.business_unit = BusinessUnit.objects.create(
            name="Tech", code="TECH", manager=self.bu_manager
        )
        self.offer_payload = {
            "title": "Software Engineer Intern",
            "description": "Join our team",
            "business_unit": self.business_unit.id,
            "application_type": ApplicationType.PFE_INTERNSHIP,
        }

    def test_super_admin_can_create_offer(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post("/api/offers/", self.offer_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Offer.objects.count(), 1)
        self.assertEqual(Offer.objects.first().status, OfferStatus.DRAFT)

    def test_hr_can_create_offer(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.post("/api/offers/", self.offer_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created_by_email"], self.hr.email)

    def test_candidate_cannot_create_offer(self):
        self.client.force_authenticate(user=self.candidate)
        response = self.client.post("/api/offers/", self.offer_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_publish_offer(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post("/api/offers/", self.offer_payload)
        offer_id = response.data["id"]
        response_publish = self.client.post(f"/api/offers/{offer_id}/publish/")
        self.assertEqual(response_publish.status_code, status.HTTP_200_OK)
        self.assertEqual(Offer.objects.get(id=offer_id).status, OfferStatus.PUBLISHED)

    def test_hr_can_read_all_offers(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post("/api/offers/", self.offer_payload)
        offer_id = response.data["id"]

        self.client.force_authenticate(user=self.hr)
        response_get = self.client.get(f"/api/offers/{offer_id}/")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)

        response_list = self.client.get("/api/offers/")
        self.assertEqual(response_list.data["count"], 1)

    def test_candidate_can_read_only_published_offers(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post("/api/offers/", self.offer_payload)
        offer_id = response.data["id"]

        self.client.force_authenticate(user=self.candidate)
        response_get_draft = self.client.get(f"/api/offers/{offer_id}/")
        self.assertEqual(response_get_draft.status_code, status.HTTP_404_NOT_FOUND)
        response_list_draft = self.client.get("/api/offers/")
        self.assertEqual(response_list_draft.data["count"], 0)

        self.client.force_authenticate(user=self.super_admin)
        self.client.post(f"/api/offers/{offer_id}/publish/")

        self.client.force_authenticate(user=self.candidate)
        response_get_published = self.client.get(f"/api/offers/{offer_id}/")
        self.assertEqual(response_get_published.status_code, status.HTTP_200_OK)
        response_list_published = self.client.get("/api/offers/")
        self.assertEqual(response_list_published.data["count"], 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class InternshipWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="intern-admin@example.com", password="pwd")
        self.hr = User.objects.create_user(email="intern-hr@example.com", password="pwd", role=UserRole.HR)
        self.manager = User.objects.create_user(email="intern-manager@example.com", password="pwd", role=UserRole.BU_MANAGER)
        self.supervisor = User.objects.create_user(email="supervisor@example.com", password="pwd", role=UserRole.EMPLOYEE)
        self.other_supervisor = User.objects.create_user(email="other-supervisor@example.com", password="pwd", role=UserRole.EMPLOYEE)
        self.intern_user = User.objects.create_user(email="intern@example.com", password="pwd", role=UserRole.INTERN)
        self.other_intern_user = User.objects.create_user(email="other-intern@example.com", password="pwd", role=UserRole.INTERN)
        self.bu = BusinessUnit.objects.create(name="Intern BU", code="INT", manager=self.manager)
        self.profile = InternProfile.objects.create(user=self.intern_user, business_unit=self.bu, supervisor=self.supervisor)
        self.other_profile = InternProfile.objects.create(user=self.other_intern_user, business_unit=self.bu, supervisor=self.other_supervisor)

    def test_hr_can_assign_bu_supervisor_dates_and_status(self):
        self.client.force_authenticate(self.hr)
        response = self.client.patch(f"/api/interns/{self.profile.id}/", {
            "business_unit": self.bu.id, "supervisor": self.other_supervisor.id,
            "internship_start": "2026-08-01", "internship_end": "2026-12-01",
            "current_status": "ACTIVE", "progress": 15,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.supervisor, self.other_supervisor)
        self.assertEqual(self.profile.progress, 15)

    def test_supervisor_can_update_progress_but_not_assignment(self):
        self.client.force_authenticate(self.supervisor)
        response = self.client.patch(f"/api/interns/{self.profile.id}/", {"progress": 45, "current_status": "ACTIVE"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        forbidden = self.client.patch(f"/api/interns/{self.profile.id}/", {"school": "Changed"})
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_intern_can_upload_and_download_own_document_only(self):
        self.client.force_authenticate(self.intern_user)
        upload = SimpleUploadedFile("agreement.pdf", b"%PDF-1.4 internship", content_type="application/pdf")
        response = self.client.post("/api/intern-documents/", {"intern": self.profile.id, "document_type": "CONVENTION", "file": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document_id = response.data["id"]
        download = self.client.get(f"/api/intern-documents/{document_id}/download/")
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        other_upload = SimpleUploadedFile("other.pdf", b"%PDF-1.4 other", content_type="application/pdf")
        forbidden = self.client.post("/api/intern-documents/", {"intern": self.other_profile.id, "document_type": "OTHER", "file": other_upload}, format="multipart")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_can_validate_document(self):
        document = InternDocument.objects.create(intern=self.profile, document_type="NDA", file=SimpleUploadedFile("nda.pdf", b"nda"))
        self.client.force_authenticate(self.hr)
        response = self.client.post(f"/api/intern-documents/{document.id}/validate/", {"comment": "Conforme"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertTrue(document.is_validated)
        self.assertEqual(document.validator, self.hr)

    def test_assigned_supervisor_can_create_evaluation_only_for_assigned_intern(self):
        payload = {"intern": self.profile.id, "evaluation_type": "MIDTERM", "technical_skills": 4, "autonomy": 4, "communication": 4, "teamwork": 5, "deadline_respect": 4, "work_quality": 4, "professionalism": 5, "overall_score": 4.3, "comments": "Bon progrès"}
        self.client.force_authenticate(self.supervisor)
        response = self.client.post("/api/intern-evaluations/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InternEvaluation.objects.get().evaluator, self.supervisor)
        payload["intern"] = self.other_profile.id
        forbidden = self.client.post("/api/intern-evaluations/", payload)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_intern_and_supervisor_querysets_are_scoped(self):
        self.client.force_authenticate(self.intern_user)
        intern_list = self.client.get("/api/interns/")
        self.assertEqual(intern_list.data["count"], 1)
        self.client.force_authenticate(self.supervisor)
        supervisor_list = self.client.get("/api/interns/")
        self.assertEqual(supervisor_list.data["count"], 1)

