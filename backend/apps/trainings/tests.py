from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import User
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from .models import ClientProfile, Training, TrainingSession, TrainingEnrollment
from .choices import TrainingType, DeliveryMode, TrainingStatus, SessionStatus, EnrollmentStatus

class TrainingsAPITestCase(APITestCase):
    def setUp(self):
        # Clean up database from migration seeds
        Training.objects.all().delete()
        # Create Super Admin
        self.super_admin = User.objects.create_user(
            email="admin@test.com", password="pwd", role=UserRole.SUPER_ADMIN
        )
        
        # Create HR
        self.hr = User.objects.create_user(
            email="hr@test.com", password="pwd", role=UserRole.HR
        )
        
        # Create BU Manager
        self.bu_manager = User.objects.create_user(
            email="manager@test.com", password="pwd", role=UserRole.BU_MANAGER
        )
        self.bu = BusinessUnit.objects.create(
            name="IT Department", code="IT", manager=self.bu_manager
        )
        
        # Create Employee
        self.employee = User.objects.create_user(
            email="emp@test.com", password="pwd", role=UserRole.EMPLOYEE
        )
        BusinessUnitMembership.objects.create(
            user=self.employee, business_unit=self.bu, is_active=True
        )
        
        # Create Trainer
        self.trainer = User.objects.create_user(
            email="trainer@test.com", password="pwd", role=UserRole.TRAINER_TUTOR
        )
        
        # Create Clients
        self.client_user1 = User.objects.create_user(
            email="client1@test.com", password="pwd", role=UserRole.CLIENT
        )
        self.client_profile1 = ClientProfile.objects.create(
            user=self.client_user1, company_name="Company 1", project_info="Project A"
        )
        
        self.client_user2 = User.objects.create_user(
            email="client2@test.com", password="pwd", role=UserRole.CLIENT
        )
        self.client_profile2 = ClientProfile.objects.create(
            user=self.client_user2, company_name="Company 2", project_info="Project B"
        )
        
        # Create Base Data
        self.training_data = {
            "title": "Python Basics",
            "description": "Learn Python",
            "training_type": TrainingType.INTERNAL,
            "category": "Programming",
            "objectives": "Learn syntax",
            "duration": 40,
            "delivery_mode": DeliveryMode.ON_SITE,
            "level": "Beginner",
            "status": TrainingStatus.DRAFT
        }

    def test_super_admin_create_training(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post("/api/trainings/", self.training_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Training.objects.count(), 1)

    def test_hr_can_only_read_training_catalogue(self):
        """HR can GET the training list, but cannot create/update/delete trainings."""
        # Create a PUBLISHED training so HR can see it
        published_training = Training.objects.create(
            **{**self.training_data, "title": "Published Python", "status": TrainingStatus.PUBLISHED}
        )
        self.client.force_authenticate(user=self.hr)

        # HR can read the catalogue
        res = self.client.get("/api/trainings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in res.data["results"]]
        self.assertIn("Published Python", titles)

        # HR cannot create trainings
        res = self.client.post("/api/trainings/", self.training_data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # HR cannot update trainings
        res = self.client.patch(f"/api/trainings/{published_training.id}/", {"title": "Changed"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # HR cannot delete trainings
        res = self.client.delete(f"/api/trainings/{published_training.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_only_sees_published_trainings_not_draft_or_archived(self):
        """HR queryset is restricted to PUBLISHED internal trainings.

        HR must NOT see DRAFT or ARCHIVED trainings — those are internal
        Super-Admin management states that HR has no business viewing.
        Only PUBLISHED, non-client-reserved trainings are exposed to HR.
        """
        # DRAFT (default from training_data) — HR must NOT see this
        Training.objects.create(**self.training_data)
        # PUBLISHED — HR must see this
        published = Training.objects.create(
            **{**self.training_data, "title": "Published Course", "status": TrainingStatus.PUBLISHED}
        )
        # ARCHIVED — HR must NOT see this
        archived = Training.objects.create(
            **{**self.training_data, "title": "Archived Course", "status": TrainingStatus.ARCHIVED}
        )

        self.client.force_authenticate(user=self.hr)
        res = self.client.get("/api/trainings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = {r["title"] for r in res.data["results"]}
        self.assertIn("Published Course", titles, "HR must see published trainings.")
        self.assertNotIn("Python Basics", titles, "HR must NOT see DRAFT trainings.")
        self.assertNotIn("Archived Course", titles, "HR must NOT see ARCHIVED trainings.")

        # Super Admin sees everything
        self.client.force_authenticate(user=self.super_admin)
        res_admin = self.client.get("/api/trainings/")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        all_titles = {r["title"] for r in res_admin.data["results"]}
        self.assertIn("Python Basics", all_titles, "Super Admin must see DRAFT trainings.")
        self.assertIn("Published Course", all_titles)
        self.assertIn("Archived Course", all_titles, "Super Admin must see ARCHIVED trainings.")


    def test_bu_manager_cannot_access_training_catalogue(self):
        # Create training without BU
        Training.objects.create(**self.training_data)
        # Create training restricted to BU
        t2 = Training.objects.create(**{**self.training_data, "title": "T2", "business_unit": self.bu})
        # Create training restricted to another BU
        bu2 = BusinessUnit.objects.create(name="HR Dept", code="HRD", manager=self.super_admin)
        t3 = Training.objects.create(**{**self.training_data, "title": "T3", "business_unit": bu2})

        self.client.force_authenticate(user=self.bu_manager)
        res = self.client.get("/api/trainings/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_bu_manager_accesses_workflow_but_not_catalogue_administration(self):
        self.client.force_authenticate(user=self.bu_manager)
        for url in ["/api/trainings/", "/api/training-sessions/"]:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN, url)
        for url in ["/api/enrollments/", "/api/attendance/", "/api/certificates/"]:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)

    def test_employee_cannot_access_administrative_catalogue(self):
        # Currently DRAFT
        t1 = Training.objects.create(**self.training_data)
        t1.status = TrainingStatus.PUBLISHED
        t1.save()
        
        # Draft training
        t2 = Training.objects.create(**{**self.training_data, "title": "Draft Training"})
        
        self.client.force_authenticate(user=self.employee)
        res = self.client.get("/api/trainings/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_trainer_visibility(self):
        t1 = Training.objects.create(**self.training_data, trainer=self.trainer)
        t2 = Training.objects.create(**{**self.training_data, "title": "Other"})
        
        self.client.force_authenticate(user=self.trainer)
        res = self.client.get("/api/trainings/")
        titles = [r['title'] for r in res.data['results']]
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0], "Python Basics")

    def test_trainer_dashboard_returns_only_explicit_assignments(self):
        directly_assigned = Training.objects.create(
            **{**self.training_data, "title": "Direct assignment", "trainer": self.trainer, "business_unit": self.bu}
        )
        direct_session = TrainingSession.objects.create(
            training=directly_assigned,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=3),
            start_time="09:00", end_time="17:00", maximum_participants=10,
            trainer=self.trainer, location="Room A",
        )
        session_training = Training.objects.create(**{**self.training_data, "title": "Session assignment"})
        assigned_session = TrainingSession.objects.create(
            training=session_training,
            start_date=timezone.localdate() + timedelta(days=4),
            end_date=timezone.localdate() + timedelta(days=5),
            start_time="09:00", end_time="17:00", maximum_participants=10,
            trainer=self.trainer, location="Room B",
        )
        TrainingSession.objects.create(
            training=session_training,
            start_date=timezone.localdate() + timedelta(days=6),
            end_date=timezone.localdate() + timedelta(days=7),
            start_time="09:00", end_time="17:00", maximum_participants=10,
            trainer=None, location="Secret room",
        )
        Training.objects.create(**{**self.training_data, "title": "Not assigned"})

        self.client.force_authenticate(self.trainer)
        response = self.client.get("/api/trainings/trainer-dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        by_title = {item["title"]: item for item in response.data["results"]}
        self.assertEqual([item["id"] for item in by_title["Direct assignment"]["sessions"]], [direct_session.id])
        self.assertEqual([item["id"] for item in by_title["Session assignment"]["sessions"]], [assigned_session.id])
        self.assertEqual(by_title["Direct assignment"]["business_unit"]["name"], self.bu.name)
        self.assertIsNone(by_title["Direct assignment"]["requesting_manager"])

    def test_trainer_dashboard_rejects_other_roles(self):
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.get("/api/trainings/trainer-dashboard/").status_code, status.HTTP_403_FORBIDDEN)

    def test_client_visibility_and_restrictions(self):
        # Create Client Training
        t1 = Training.objects.create(**{**self.training_data, "title": "Client 1 Course"}, external_client=self.client_profile1)
        t2 = Training.objects.create(**{**self.training_data, "title": "Client 2 Course"}, external_client=self.client_profile2)
        
        self.client.force_authenticate(user=self.client_user1)
        
        # Standard endpoints should be forbidden or return 0 for client (due to IsNotClientProfile or get_queryset)
        res = self.client.get("/api/trainings/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Client endpoint
        res = self.client.get("/api/client/trainings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [r['title'] for r in res.data['results']]
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0], "Client 1 Course")
        
        # Ensure confidential fields are excluded (e.g. objectives shouldn't be there)
        self.assertNotIn('objectives', res.data['results'][0])

    def test_super_admin_actions(self):
        t1 = Training.objects.create(**self.training_data)
        self.client.force_authenticate(user=self.super_admin)
        
        res = self.client.post(f"/api/trainings/{t1.id}/publish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        t1.refresh_from_db()
        self.assertEqual(t1.status, TrainingStatus.PUBLISHED)
        
        res = self.client.post(f"/api/trainings/{t1.id}/archive/")
        t1.refresh_from_db()
        self.assertEqual(t1.status, TrainingStatus.ARCHIVED)

    def test_session_creation_and_validation(self):
        t1 = Training.objects.create(**self.training_data)
        self.client.force_authenticate(user=self.super_admin)
        
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.localdate()
        
        session_data = {
            "training": t1.id,
            "start_date": (today + timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=5)).isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "location": "Room A",
            "maximum_participants": 20
        }
        
        res = self.client.post("/api/training-sessions/", session_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Validation: start date after end date
        session_data["start_date"] = (today + timedelta(days=6)).isoformat()
        res = self.client.post("/api/training-sessions/", session_data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Validation: capacity zero
        session_data["start_date"] = (today + timedelta(days=1)).isoformat()
        session_data["maximum_participants"] = 0
        res = self.client.post("/api/training-sessions/", session_data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Validation: remote needs online link
        t1.delivery_mode = DeliveryMode.REMOTE
        t1.save()
        session_data["maximum_participants"] = 20
        res = self.client.post("/api/training-sessions/", session_data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST) # no online_link provided

    def test_session_actions(self):
        t1 = Training.objects.create(**self.training_data)
        s1 = TrainingSession.objects.create(
            training=t1, start_date=timezone.localdate() + timedelta(days=5), end_date=timezone.localdate() + timedelta(days=9),
            start_time="09:00", end_time="17:00", maximum_participants=10,
            location="Room A"
        )
        self.client.force_authenticate(user=self.super_admin)
        
        res = self.client.post(f"/api/training-sessions/{s1.id}/open_registration/")
        s1.refresh_from_db()
        self.assertEqual(s1.status, SessionStatus.OPEN)
        
        res = self.client.post(f"/api/training-sessions/{s1.id}/close_registration/")
        s1.refresh_from_db()
        self.assertEqual(s1.status, SessionStatus.FULL)
        
        res = self.client.post(f"/api/training-sessions/{s1.id}/complete/")
        s1.refresh_from_db()
        self.assertEqual(s1.status, SessionStatus.COMPLETED)
        
        # Cannot update completed session
        res = self.client.patch(f"/api/training-sessions/{s1.id}/", {"location": "Room B"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_and_filter(self):
        Training.objects.create(**{**self.training_data, "title": "Django Basics"})
        Training.objects.create(**{**self.training_data, "title": "React Basics", "category": "Frontend"})
        
        self.client.force_authenticate(user=self.super_admin)
        # Filter
        res = self.client.get("/api/trainings/?category=Frontend")
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['title'], "React Basics")
        
        # Search
        res = self.client.get("/api/trainings/?search=Django")
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['title'], "Django Basics")


class TrainingEnrollmentAPITestCase(APITestCase):
    def setUp(self):
        # Clean up database from migration seeds
        Training.objects.all().delete()
        self.super_admin = User.objects.create_user(email="admin_e@test.com", password="pwd", role=UserRole.SUPER_ADMIN)
        self.hr = User.objects.create_user(email="hr_e@test.com", password="pwd", role=UserRole.HR)
        
        self.manager1 = User.objects.create_user(email="mgr1@test.com", password="pwd", role=UserRole.BU_MANAGER)
        self.manager2 = User.objects.create_user(email="mgr2@test.com", password="pwd", role=UserRole.BU_MANAGER)
        
        self.bu1 = BusinessUnit.objects.create(name="BU1", code="CBU1", manager=self.manager1)
        self.bu2 = BusinessUnit.objects.create(name="BU2", code="CBU2", manager=self.manager2)
        
        BusinessUnitMembership.objects.create(business_unit=self.bu1, user=self.manager1, position="Manager")
        BusinessUnitMembership.objects.create(business_unit=self.bu2, user=self.manager2, position="Manager")
        
        self.employee1 = User.objects.create_user(email="emp1@test.com", password="pwd", role=UserRole.EMPLOYEE)
        self.employee2 = User.objects.create_user(email="emp2@test.com", password="pwd", role=UserRole.EMPLOYEE)
        
        BusinessUnitMembership.objects.create(business_unit=self.bu1, user=self.employee1, position="Emp")
        BusinessUnitMembership.objects.create(business_unit=self.bu2, user=self.employee2, position="Emp")
        
        self.trainer = User.objects.create_user(email="trainer_e@test.com", password="pwd", role=UserRole.TRAINER_TUTOR)
        
        self.training = Training.objects.create(
            title="Test Course", description="Desc", training_type=TrainingType.INTERNAL,
            category="IT", objectives="Obj", duration=10, delivery_mode=DeliveryMode.ON_SITE,
            level="Beginner"
        )
        self.session = TrainingSession.objects.create(
            training=self.training, start_date=timezone.localdate() - timedelta(days=2), end_date=timezone.localdate() - timedelta(days=1),
            start_time="09:00", end_time="17:00", maximum_participants=2, trainer=self.trainer,
            location="Room A"
        )
        
    def test_employee_cannot_submit_through_admin_enrollment_workflow(self):
        self.client.force_authenticate(user=self.employee1)
        res = self.client.post("/api/enrollments/", {"training": self.training.id, "session": self.session.id})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_approve_managed_bu_enrollment(self):
        enr = TrainingEnrollment.objects.create(user=self.employee1, training=self.training, session=self.session)
        
        self.client.force_authenticate(user=self.manager1)
        res = self.client.post(f"/api/enrollments/{enr.id}/manager_approve/", {"approved": True, "comment": "OK"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        enr.refresh_from_db()
        self.assertEqual(enr.status, EnrollmentStatus.PENDING_SUPER_ADMIN)
        
    def test_manager_can_reject_managed_bu_enrollment(self):
        enr = TrainingEnrollment.objects.create(user=self.employee1, training=self.training, session=self.session)
        
        self.client.force_authenticate(user=self.manager1)
        res = self.client.post(f"/api/enrollments/{enr.id}/manager_reject/", {"approved": False})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        enr.refresh_from_db()
        self.assertEqual(enr.status, EnrollmentStatus.REJECTED_BY_MANAGER)

    def test_manager_boundaries(self):
        enr = TrainingEnrollment.objects.create(user=self.employee1, training=self.training, session=self.session)
        
        # Manager2 (different BU) tries to approve
        self.client.force_authenticate(user=self.manager2)
        res = self.client.post(f"/api/enrollments/{enr.id}/manager_approve/", {"approved": True})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        
        # Manager tries to approve own request
        enr_own = TrainingEnrollment.objects.create(user=self.manager1, training=self.training, session=self.session)
        self.client.force_authenticate(user=self.manager1)
        res = self.client.post(f"/api/enrollments/{enr_own.id}/manager_approve/", {"approved": True})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_hr_forbidden_write(self):
        enr = TrainingEnrollment.objects.create(user=self.employee1, training=self.training, session=self.session)
        self.client.force_authenticate(user=self.hr)
        
        # HR has no access to enrollment operations.
        res = self.client.get("/api/enrollments/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Write forbidden
        res = self.client.post(f"/api/enrollments/{enr.id}/super_admin_approve/", {"approved": True})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_direct_enrollment_and_capacity(self):
        self.client.force_authenticate(user=self.super_admin)
        
        res1 = self.client.post("/api/enrollments/direct_enrollment/", {
            "user": self.employee1.id, "training": self.training.id, "session": self.session.id
        })
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        res2 = self.client.post("/api/enrollments/direct_enrollment/", {
            "user": self.employee2.id, "training": self.training.id, "session": self.session.id
        })
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, SessionStatus.FULL)
        
        # Try a third, should fail capacity
        res3 = self.client.post("/api/enrollments/direct_enrollment/", {
            "user": self.manager1.id, "training": self.training.id, "session": self.session.id
        })
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Super admin cancel one
        enr_id = res1.data['id']
        res_cancel = self.client.post(f"/api/enrollments/{enr_id}/cancel/")
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, SessionStatus.OPEN)
        
    def test_visibility_scope(self):
        enr = TrainingEnrollment.objects.create(user=self.employee1, training=self.training, session=self.session)
        
        # Trainer sees only assigned
        self.client.force_authenticate(user=self.trainer)
        res = self.client.get("/api/enrollments/")
        self.assertEqual(len(res.data['results']), 1)

    def test_generic_enrollment_mutations_are_disabled(self):
        enrollment = TrainingEnrollment.objects.create(
            user=self.employee1, training=self.training, session=self.session
        )
        self.client.force_authenticate(user=self.manager1)
        response = self.client.patch(
            f"/api/enrollments/{enrollment.id}/",
            {"status": EnrollmentStatus.ENROLLED},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, EnrollmentStatus.PENDING_MANAGER)
        
        # Employee sees only own
        self.client.force_authenticate(user=self.employee2)
        res = self.client.get("/api/enrollments/")
        self.assertEqual(len(res.data['results']), 0)
        
        # Super admin sees all
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/enrollments/")
        self.assertEqual(len(res.data['results']), 1)


from django.test import TestCase

class TrainingsCatalogSeedingTests(TestCase):
    def test_catalogue_seeded_successfully(self):
        """Les formations et modules doivent exister en base après la migration."""
        # Main trainings
        main_titles = ["CCNA", "DCCOR", "ENCOR", "SCOR", "Infoblox", "Palo Alto", "PMP"]
        for title in main_titles:
            self.assertTrue(
                Training.objects.filter(title=title).exists(),
                f"La formation principale {title} devrait être enregistrée."
            )

        # Verifier les catégories
        self.assertEqual(Training.objects.get(title="CCNA").category, "Réseaux")
        self.assertEqual(Training.objects.get(title="DCCOR").category, "CCNP")
        self.assertEqual(Training.objects.get(title="ENCOR").category, "CCNP")
        self.assertEqual(Training.objects.get(title="SCOR").category, "CCNP")
        self.assertEqual(Training.objects.get(title="Infoblox").category, "Réseaux")
        self.assertEqual(Training.objects.get(title="Palo Alto").category, "Sécurité")
        self.assertEqual(Training.objects.get(title="PMP").category, "Gestion de projet")

        # Modules check
        ccna_mod_count = Training.objects.filter(category="CCNA").count()
        self.assertEqual(ccna_mod_count, 12, "CCNA doit avoir 12 modules.")

        dccor_mod_count = Training.objects.filter(category="DCCOR").count()
        self.assertEqual(dccor_mod_count, 6, "DCCOR doit avoir 6 modules.")

        encor_mod_count = Training.objects.filter(category="ENCOR").count()
        self.assertEqual(encor_mod_count, 11, "ENCOR doit avoir 11 modules.")

        scor_mod_count = Training.objects.filter(category="SCOR").count()
        self.assertEqual(scor_mod_count, 5, "SCOR doit avoir 5 modules.")

        infoblox_mod_count = Training.objects.filter(category="Infoblox").count()
        self.assertEqual(infoblox_mod_count, 3, "Infoblox doit avoir 3 modules.")

        palo_alto_mod_count = Training.objects.filter(category="Palo Alto").count()
        self.assertEqual(palo_alto_mod_count, 4, "Palo Alto doit avoir 4 modules.")

        pmp_mod_count = Training.objects.filter(category="PMP").count()
        self.assertEqual(pmp_mod_count, 4, "PMP doit avoir 4 modules.")

    def test_catalogue_idempotence(self):
        """Exécuter à nouveau la logique de seed ne doit pas créer de doublons."""
        initial_count = Training.objects.count()

        # Simuler un second appel à seed_catalogue en utilisant importlib
        import importlib
        seed_module = importlib.import_module("apps.trainings.migrations.0007_seed_internal_trainings")
        seed_catalogue = seed_module.seed_catalogue

        class DummyApp:
            def get_model(self, app_label, model_name):
                return Training
        seed_catalogue(DummyApp(), None)

        final_count = Training.objects.count()
        self.assertEqual(initial_count, final_count, "Le seed ne doit pas recréer de doublons.")
