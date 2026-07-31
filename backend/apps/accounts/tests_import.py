from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import EmployeeProfile
from apps.accounts.services.account_generation import generate_professional_email

User = get_user_model()

class BulkImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            email="admin@finatech.com", 
            password="pwd", 
            role=UserRole.SUPER_ADMIN
        )
        self.hr_user = User.objects.create_user(
            email="hr@finatech.com", 
            password="pwd", 
            role=UserRole.HR
        )
        self.bu = BusinessUnit.objects.create(name="IT", code="BU_IT", manager=self.super_admin)

    def test_super_admin_access(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(reverse("import-preview"))
        self.assertNotEqual(response.status_code, 403)

    def test_hr_denial(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(reverse("import-preview"))
        self.assertEqual(response.status_code, 403)

    def test_csv_parsing_and_valid_roles(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = b"Pr\xc3\xa9nom,Nom,Email personnel,T\xc3\xa9l\xc3\xa9phone,Profil,BU,Poste\nJean,Dupont,jean@personal.com,1234,EMPLOYEE,BU_IT,Dev"
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1)
        self.assertEqual(data["invalid_count"], 0)

    def test_missing_columns_and_invalid_data(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = b"Pr\xc3\xa9nom,Nom,Email personnel,Profil,BU\n,Dupont,invalid_email,INVALID_ROLE,BU_FAKE"
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 0)
        self.assertEqual(data["invalid_count"], 1)
        errors = data["invalid_rows"][0]["errors"]
        error_text = " ".join(errors)
        self.assertIn("Prénom est requis", error_text)
        self.assertIn("Format d'email invalide", error_text)
        self.assertIn("Rôle ou profil invalide", error_text)
        self.assertIn("BU_FAKE", data["missing_bus"])

    def test_email_collision(self):
        User.objects.create_user(email="jean.dupont@finatech.com", password="pwd")
        email = generate_professional_email("Jean", "Dupont")
        self.assertEqual(email, "jean.dupont2@finatech.com")

    def test_import_execution(self):
        self.client.force_authenticate(user=self.super_admin)
        valid_rows = [{
            "row": 2,
            "payload": {
                "first_name": "Marc",
                "last_name": "Lafayette",
                "contact_email": "marc@perso.com",
                "phone_number": "",
                "role": UserRole.EMPLOYEE,
                "business_unit": self.bu.id,
                "position": "Dev",
                "supervisor": None
            }
        }]
        response = self.client.post(reverse("import-confirm"), {"valid_rows": valid_rows}, format="json")
        self.assertEqual(response.status_code, 200)
        
        user = User.objects.get(contact_email="marc@perso.com")
        self.assertEqual(user.email, "marc.lafayette@finatech.com")
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.check_password(response.json()["results"][0]["Mot de passe temporaire"]))
        self.assertTrue(EmployeeProfile.objects.filter(user=user).exists())
        self.assertTrue(BusinessUnitMembership.objects.filter(user=user, business_unit=self.bu).exists())
