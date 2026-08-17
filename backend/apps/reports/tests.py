from datetime import date
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership, BusinessUnitNeed
from apps.business_units.choices import NeedStatus
from apps.recruitment.models import InternProfile
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
        self.assertEqual(response.status_code,status.HTTP_200_OK); self.assertEqual(response.data["cards"]["projects"],1); self.assertIn("attendance",response.data["series"]); self.assertIn("monthly_internships",response.data["series"]); self.assertIn("certificate_rate",response.data["kpis"])

    def test_hr_can_access_read_only_global_summary(self):
        self.client.force_authenticate(self.hr)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recent_activities"], [])

    def test_other_roles_are_denied(self):
        self.client.force_authenticate(self.employee); self.assertEqual(self.client.get("/api/reports/summary/").status_code,status.HTTP_403_FORBIDDEN)

    def test_manager_summary_is_scoped_to_managed_business_unit(self):
        self.bu.manager = self.manager
        self.bu.save(update_fields=["manager"])
        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cards"]["projects"], 1)
        self.assertEqual(response.data["filters"]["business_unit"], "")

    def test_manager_dashboard_contains_only_managed_bu_data(self):
        other_manager = User.objects.create_user(email="other-manager@test.com", password="pwd", role=UserRole.BU_MANAGER)
        other_employee = User.objects.create_user(email="other-employee@test.com", password="pwd", role=UserRole.EMPLOYEE)
        other_bu = BusinessUnit.objects.create(name="Other BU", code="OTHER", manager=other_manager)
        BusinessUnitMembership.objects.create(user=other_employee, business_unit=other_bu, is_active=True)
        BusinessUnitNeed.objects.create(business_unit=self.bu, title="Own need", description="Own", status=NeedStatus.SUBMITTED, created_by=self.manager)
        BusinessUnitNeed.objects.create(business_unit=other_bu, title="Secret need", description="Other", status=NeedStatus.SUBMITTED, created_by=other_manager)
        intern = User.objects.create_user(email="intern@test.com", password="pwd", role=UserRole.INTERN)
        InternProfile.objects.create(user=intern, business_unit=self.bu)

        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/reports/business-unit-dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["open_needs"], 1)
        self.assertEqual(response.data["counts"]["collaborators"], 1)
        self.assertEqual(response.data["counts"]["interns"], 1)
        self.assertEqual([item["title"] for item in response.data["recent_needs"]], ["Own need"])
        self.assertNotIn(other_bu.id, [item["id"] for item in response.data["business_units"]])

    def test_business_unit_dashboard_is_manager_only(self):
        for user in [self.admin, self.hr, self.employee]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/reports/business-unit-dashboard/").status_code, status.HTTP_403_FORBIDDEN)

    def test_summary_exposes_smart_cards_filters_and_insights(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/reports/summary/?training_type=INTERNAL")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("active_offers", response.data["cards"])
        self.assertIn("validated_attendance", response.data["cards"])
        self.assertIn("filter_options", response.data)
        self.assertIn("insights", response.data)

    def test_business_unit_filter_scopes_cards(self):
        self.client.force_authenticate(self.admin); response=self.client.get(f"/api/reports/summary/?business_unit={self.bu.id}")
        self.assertEqual(response.data["cards"]["projects"],1); self.assertEqual(response.data["cards"]["users"],1); self.assertEqual(response.data["cards"]["business_units"],1)

    def test_csv_and_pdf_exports(self):
        self.client.force_authenticate(self.admin); csv_response=self.client.get("/api/reports/export/csv/"); self.assertEqual(csv_response.status_code,200); self.assertEqual(csv_response["Content-Type"],"text/csv"); self.assertIn(b"cards,projects,1",csv_response.content)
        pdf_response=self.client.get("/api/reports/export/pdf/"); self.assertEqual(pdf_response["Content-Type"],"application/pdf"); self.assertTrue(pdf_response.content.startswith(b"%PDF"))

    def test_hr_can_access_hr_dashboard(self):
        self.client.force_authenticate(self.hr)
        response = self.client.get("/api/reports/hr-dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("active_interns", response.data)
        self.assertIn("missing_documents", response.data)

    def test_other_roles_cannot_access_hr_dashboard(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/reports/hr-dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/reports/hr-dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
