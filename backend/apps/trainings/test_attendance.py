from datetime import date, time
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.choices import UserRole
from apps.accounts.models import User
from .choices import DeliveryMode, EnrollmentStatus, SessionStatus, TrainingStatus, TrainingType
from .models import AttendanceHistory, SessionAttendance, Training, TrainingCertificate, TrainingEnrollment, TrainingSession


class AttendanceCertificateTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin-att@test.com", password="pwd", role=UserRole.SUPER_ADMIN)
        self.hr = User.objects.create_user(email="hr-att@test.com", password="pwd", role=UserRole.HR)
        self.trainer = User.objects.create_user(email="trainer-att@test.com", password="pwd", role=UserRole.TRAINER_TUTOR)
        self.other_trainer = User.objects.create_user(email="other-att@test.com", password="pwd", role=UserRole.TRAINER_TUTOR)
        self.employee = User.objects.create_user(email="student-att@test.com", password="pwd", role=UserRole.EMPLOYEE, first_name="Student")
        self.outsider = User.objects.create_user(email="outsider-att@test.com", password="pwd", role=UserRole.EMPLOYEE)
        self.training = Training.objects.create(title="Django", description="Course", training_type=TrainingType.INTERNAL, category="Tech", objectives="Build", duration=8, delivery_mode=DeliveryMode.ON_SITE, level="Intro", status=TrainingStatus.PUBLISHED, created_by=self.admin)
        self.session = TrainingSession.objects.create(training=self.training, start_date=date.today(), end_date=date.today(), start_time=time(9), end_time=time(17), location="Room", trainer=self.trainer, maximum_participants=10, status=SessionStatus.IN_PROGRESS, created_by=self.admin)
        self.enrollment = TrainingEnrollment.objects.create(user=self.employee, training=self.training, session=self.session, status=EnrollmentStatus.ENROLLED, final_status=EnrollmentStatus.ENROLLED)

    def tearDown(self):
        for certificate in TrainingCertificate.objects.all():
            if certificate.file and default_storage.exists(certificate.file.name):
                default_storage.delete(certificate.file.name)

    def test_assigned_trainer_records_and_validates_with_history(self):
        self.client.force_authenticate(self.trainer)
        created = self.client.post("/api/attendance/", {"enrollment": self.enrollment.id, "status": "PRESENT", "note": "On time"})
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        validated = self.client.post(f"/api/attendance/{created.data['id']}/validate/", {})
        self.assertEqual(validated.status_code, status.HTTP_200_OK)
        self.assertTrue(validated.data["validated"])
        self.assertEqual(AttendanceHistory.objects.count(), 2)

    def test_unassigned_trainer_and_hr_cannot_write(self):
        self.client.force_authenticate(self.other_trainer)
        denied = self.client.post("/api/attendance/", {"enrollment": self.enrollment.id, "status": "PRESENT"})
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.hr)
        denied = self.client.post("/api/attendance/", {"enrollment": self.enrollment.id, "status": "PRESENT"})
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get("/api/attendance/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get("/api/certificates/").status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_sees_only_own_attendance(self):
        SessionAttendance.objects.create(enrollment=self.enrollment, status="PRESENT", recorded_by=self.admin)
        self.client.force_authenticate(self.employee)
        own = self.client.get("/api/attendance/")
        self.assertEqual(own.data["count"], 1)
        self.client.force_authenticate(self.outsider)
        outside = self.client.get("/api/attendance/")
        self.assertEqual(outside.data["count"], 0)

    def test_completion_requires_validation_and_generates_secure_certificate(self):
        attendance = SessionAttendance.objects.create(enrollment=self.enrollment, status="PRESENT", recorded_by=self.trainer)
        self.client.force_authenticate(self.trainer)
        blocked = self.client.post(f"/api/training-sessions/{self.session.id}/complete/", {})
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.client.post(f"/api/attendance/{attendance.id}/validate/", {})
        completed = self.client.post(f"/api/training-sessions/{self.session.id}/complete/", {})
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.COMPLETED)
        certificate = TrainingCertificate.objects.get(enrollment=self.enrollment)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(f"/api/certificates/{certificate.id}/download/").status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.employee)
        download = self.client.get(f"/api/certificates/{certificate.id}/download/")
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(download["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(download.streaming_content).startswith(b"%PDF"))

    def test_absent_participant_is_not_completed_or_certified(self):
        attendance = SessionAttendance.objects.create(enrollment=self.enrollment, status="ABSENT", validated=True, recorded_by=self.trainer, validated_by=self.trainer)
        self.client.force_authenticate(self.trainer)
        response = self.client.post(f"/api/training-sessions/{self.session.id}/complete/", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.ENROLLED)
        self.assertFalse(TrainingCertificate.objects.filter(enrollment=self.enrollment).exists())
