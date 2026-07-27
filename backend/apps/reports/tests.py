from datetime import date
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.projects.models import Project

class ReportTests(APITestCase):
    def setUp(self):
        self.admin=User.objects.create_user(email="report-admin@test.com",password="pwd",role=UserRole.SUPER_ADMIN)
        self.hr=User.objects.create_user(email="report-hr@test.com",password="pwd",role=UserRole.HR)
        self.manager=User.objects.create_user(email="report-manager@test.com",password="pwd",role=UserRole.BU_MANAGER)
        self.employee=User.objects.create_user(email="report-employee@test.com",password="pwd",role=UserRole.EMPLOYEE)
        self.bu=BusinessUnit.objects.create(name="Analytics",code="ANA",manager=self.manager)
        BusinessUnitMembership.objects.create(user=self.employee,business_unit=self.bu,is_active=True)
        Project.objects.create(title="Metrics",description="Dashboard",business_unit=self.bu,supervisor=self.employee,start_date=date.today(),status="ACTIVE",progress=60,created_by=self.admin)

    def test_super_admin_gets_global_multidomain_summary(self):
        self.client.force_authenticate(self.admin); response=self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code,status.HTTP_200_OK); self.assertEqual(response.data["cards"]["projects"],1); self.assertIn("attendance",response.data["series"]); self.assertIn("certificate_rate",response.data["kpis"])

    def test_hr_cannot_access_global_reports(self):
        self.client.force_authenticate(self.hr); self.assertEqual(self.client.get("/api/reports/summary/").status_code,status.HTTP_403_FORBIDDEN)

    def test_other_roles_are_denied(self):
        self.client.force_authenticate(self.employee); self.assertEqual(self.client.get("/api/reports/summary/").status_code,status.HTTP_403_FORBIDDEN)

    def test_business_unit_filter_scopes_cards(self):
        self.client.force_authenticate(self.admin); response=self.client.get(f"/api/reports/summary/?business_unit={self.bu.id}")
        self.assertEqual(response.data["cards"]["projects"],1); self.assertEqual(response.data["cards"]["users"],1); self.assertEqual(response.data["cards"]["business_units"],1)

    def test_csv_and_pdf_exports(self):
        self.client.force_authenticate(self.admin); csv_response=self.client.get("/api/reports/export/csv/"); self.assertEqual(csv_response.status_code,200); self.assertEqual(csv_response["Content-Type"],"text/csv"); self.assertIn(b"cards,projects,1",csv_response.content)
        pdf_response=self.client.get("/api/reports/export/pdf/"); self.assertEqual(pdf_response["Content-Type"],"application/pdf"); self.assertTrue(pdf_response.content.startswith(b"%PDF"))
