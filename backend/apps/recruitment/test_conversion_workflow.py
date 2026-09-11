import shutil
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.notifications.models import AuditLog
from .choices import ApplicationStatus, ApplicationType
from .models import (
    Application,
    ApplicationDocument,
    ApplicationMatch,
    CandidateProfile,
    CVAnalysis,
    EmployeeProfile,
    InternProfile,
    Offer,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class CandidateConversionWorkflowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="conversion-admin@test.com", password="StrongPass123!",
        )
        self.hr = User.objects.create_user(
            email="conversion-hr@test.com", password="StrongPass123!", role=UserRole.HR,
        )
        self.manager = User.objects.create_user(
            email="conversion-manager@test.com", password="StrongPass123!",
            role=UserRole.BU_MANAGER,
        )
        self.bu = BusinessUnit.objects.create(
            name="NetSEC", code="NetSEC", manager=self.manager,
        )
        self.other_bu = BusinessUnit.objects.create(name="Achat", code="Achat")
        self.supervisor = User.objects.create_user(
            email="conversion-supervisor@test.com", password="StrongPass123!",
            role=UserRole.EMPLOYEE,
        )
        BusinessUnitMembership.objects.create(user=self.supervisor, business_unit=self.bu)

    def create_application(self, suffix="candidate", application_type=ApplicationType.HIRING):
        user = User.objects.create_user(
            email=f"{suffix}@example.com",
            password="CandidatePass123!",
            role=UserRole.CANDIDATE,
            first_name="Camille",
            last_name="Candidate",
        )
        profile = CandidateProfile.objects.create(
            user=user,
            account_email=user.email,
            account_first_name=user.first_name,
            account_last_name=user.last_name,
            phone_number="+212600000000",
            current_school="Smart School",
            study_level="MASTER",
        )
        offer = Offer.objects.create(
            title=f"Offer {suffix}", description="Description",
            business_unit=self.bu, application_type=application_type,
        )
        return Application.objects.create(
            candidate_profile=profile,
            offer=offer,
            application_type=application_type,
            status=ApplicationStatus.ACCEPTED,
            accepted_at=timezone.now(),
        )

    def convert(self, application, payload, user=None, *, multipart=False):
        self.client.force_authenticate(user=user or self.admin)
        return self.client.post(
            f"/api/applications/{application.pk}/convert/",
            payload,
            format="multipart" if multipart else "json",
        )

    def intern_payload(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        return {
            "conversion_type": "INTERN",
            "business_unit": self.bu.pk,
            "supervisor": self.supervisor.pk,
            "school": "Smart School",
            "specialization": "Cybersécurité",
            "internship_type": "PFE",
            "paid": True,
            "internship_start": tomorrow.isoformat(),
            "internship_end": (tomorrow + timedelta(days=120)).isoformat(),
            "subject_title": "Sécurisation du SI",
        }

    def test_intern_conversion_is_complete_and_preserves_login_and_history(self):
        application = self.create_application("intern", ApplicationType.PFE_INTERNSHIP)
        document = ApplicationDocument.objects.create(
            application=application,
            document_type="CV",
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 cv", content_type="application/pdf"),
            original_name="cv.pdf",
        )
        analysis = CVAnalysis.objects.create(
            application=application, source_sha256="a" * 64, raw_text="Python",
        )
        match = ApplicationMatch.objects.create(
            application=application, offer=application.offer, score="82.00",
            explanation="Match conservé",
        )
        original_user_id = application.candidate_profile.user_id
        original_email = application.candidate.email
        password_hash = application.candidate.password
        payload = self.intern_payload()
        payload["specification_pdf"] = SimpleUploadedFile(
            "specification.pdf", b"%PDF-1.4 specification", content_type="application/pdf",
        )

        response = self.convert(application, payload, multipart=True)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("password", str(response.data).lower())
        self.assertTrue(response.data["credentials_preserved"])
        self.assertEqual(response.data["login_email"], original_email)
        application.refresh_from_db()
        user = application.candidate
        user.refresh_from_db()
        profile = InternProfile.objects.get(user=user)
        self.assertEqual(user.pk, original_user_id)
        self.assertEqual(user.email, original_email)
        self.assertEqual(user.password, password_hash)
        self.assertTrue(user.check_password("CandidatePass123!"))
        self.assertEqual(user.role, UserRole.INTERN)
        self.assertEqual(profile.source_application_id, application.pk)
        self.assertEqual(profile.business_unit_id, self.bu.pk)
        self.assertEqual(profile.supervisor_id, self.supervisor.pk)
        self.assertEqual(profile.school, "Smart School")
        self.assertEqual(profile.specialization, "Cybersécurité")
        self.assertEqual(profile.subject_title, "Sécurisation du SI")
        self.assertTrue(profile.specification_pdf.name.endswith("specification.pdf"))
        self.assertEqual(user.bu_memberships.get(is_active=True).business_unit_id, self.bu.pk)
        self.assertEqual(application.status, ApplicationStatus.ACCEPTED)
        self.assertTrue(ApplicationDocument.objects.filter(pk=document.pk).exists())
        self.assertTrue(CVAnalysis.objects.filter(pk=analysis.pk).exists())
        self.assertTrue(ApplicationMatch.objects.filter(pk=match.pk).exists())
        self.assertEqual(response.data["application"]["conversion"]["type"], "INTERN")
        self.assertTrue(AuditLog.objects.filter(
            action="USER_BUSINESS_UNIT_CHANGED", target_id=str(user.pk), actor=self.admin,
        ).exists())
        self.client.force_authenticate(user=None)
        login = self.client.post(
            "/api/auth/token/",
            {"email": original_email, "password": "CandidatePass123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)

    def test_employee_conversion_creates_one_profile_and_membership(self):
        application = self.create_application("employee")
        user_id = application.candidate_profile.user_id
        response = self.convert(application, {
            "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
        })

        self.assertEqual(response.status_code, 200, response.data)
        application.refresh_from_db()
        user = application.candidate
        self.assertEqual(user.pk, user_id)
        self.assertEqual(user.role, UserRole.EMPLOYEE)
        self.assertEqual(EmployeeProfile.objects.get(user=user).source_application_id, application.pk)
        self.assertEqual(EmployeeProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(user.bu_memberships.filter(is_active=True).count(), 1)
        self.assertEqual(user.bu_memberships.get(is_active=True).business_unit_id, self.bu.pk)
        self.assertEqual(response.data["application"]["conversion"]["type"], "EMPLOYEE")

    def test_conversion_requires_an_accepted_application(self):
        application = self.create_application("pending")
        application.status = ApplicationStatus.PRESELECTED
        application.save(update_fields=["status"])
        response = self.convert(application, {
            "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
        })
        self.assertEqual(response.status_code, 400)
        application.candidate.refresh_from_db()
        self.assertEqual(application.candidate.role, UserRole.CANDIDATE)

    def test_only_super_admin_can_convert(self):
        for index, user in enumerate((self.hr, self.manager), start=1):
            application = self.create_application(f"forbidden-{index}")
            with self.subTest(role=user.role):
                response = self.convert(application, {
                    "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
                }, user=user)
                self.assertEqual(response.status_code, 403)
        application = self.create_application("self-convert")
        response = self.convert(application, {
            "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
        }, user=application.candidate)
        self.assertEqual(response.status_code, 403)

    def test_same_and_contradictory_repeated_conversions_are_rejected(self):
        scenarios = [
            ("INTERN", "INTERN"),
            ("EMPLOYEE", "EMPLOYEE"),
            ("INTERN", "EMPLOYEE"),
            ("EMPLOYEE", "INTERN"),
        ]
        for index, (first, second) in enumerate(scenarios):
            application = self.create_application(f"repeat-{index}")
            first_payload = self.intern_payload() if first == "INTERN" else {
                "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
            }
            second_payload = self.intern_payload() if second == "INTERN" else {
                "conversion_type": "EMPLOYEE", "business_unit": self.bu.pk,
            }
            with self.subTest(first=first, second=second):
                self.assertEqual(self.convert(application, first_payload).status_code, 200)
                self.assertEqual(self.convert(application, second_payload).status_code, 400)
                user_id = application.candidate_profile.user_id
                self.assertEqual(User.objects.filter(pk=user_id).count(), 1)
                self.assertLessEqual(InternProfile.objects.filter(user_id=user_id).count(), 1)
                self.assertLessEqual(EmployeeProfile.objects.filter(user_id=user_id).count(), 1)

    def test_invalid_supervisor_and_business_unit_leave_no_partial_state(self):
        foreign = User.objects.create_user(email="foreign-supervisor@test.com", role=UserRole.EMPLOYEE)
        BusinessUnitMembership.objects.create(user=foreign, business_unit=self.other_bu)
        cases = [
            ({**self.intern_payload(), "supervisor": foreign.pk}, "supervisor"),
            ({"conversion_type": "EMPLOYEE", "business_unit": 999999}, "business_unit"),
        ]
        for index, (payload, field) in enumerate(cases):
            application = self.create_application(f"invalid-{index}")
            with self.subTest(field=field):
                response = self.convert(application, payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
                application.candidate.refresh_from_db()
                self.assertEqual(application.candidate.role, UserRole.CANDIDATE)
                self.assertFalse(InternProfile.objects.filter(user=application.candidate).exists())
                self.assertFalse(EmployeeProfile.objects.filter(user=application.candidate).exists())
                self.assertFalse(application.candidate.bu_memberships.filter(is_active=True).exists())

    def test_profile_creation_error_rolls_back_account_and_membership(self):
        application = self.create_application("profile-error")
        user = application.candidate
        original_password = user.password
        with patch(
            "apps.accounts.services.account_generation.EmployeeProfile.objects.update_or_create",
            side_effect=RuntimeError("profile failure"),
        ):
            with self.assertRaises(RuntimeError):
                from .services import convert_accepted_application
                convert_accepted_application(
                    application,
                    {"conversion_type": "EMPLOYEE", "business_unit": self.bu},
                    self.admin,
                )
        user.refresh_from_db()
        self.assertEqual(user.role, UserRole.CANDIDATE)
        self.assertEqual(user.password, original_password)
        self.assertFalse(EmployeeProfile.objects.filter(user=user).exists())
        self.assertFalse(user.bu_memberships.filter(is_active=True).exists())
