import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import InternProfile
from .models import Project, ProjectComment, ProjectDeliverable, ProjectDocument


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProjectWorkflowTests(APITestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser(email="project-admin@test.com",password="pwd")
        self.hr=User.objects.create_user(email="project-hr@test.com",password="pwd",role=UserRole.HR)
        self.manager=User.objects.create_user(email="project-manager@test.com",password="pwd",role=UserRole.BU_MANAGER)
        self.supervisor=User.objects.create_user(email="project-supervisor@test.com",password="pwd",role=UserRole.EMPLOYEE)
        self.employee=User.objects.create_user(email="project-employee@test.com",password="pwd",role=UserRole.EMPLOYEE)
        self.outsider=User.objects.create_user(email="project-outsider@test.com",password="pwd",role=UserRole.EMPLOYEE)
        self.intern=User.objects.create_user(email="project-intern@test.com",password="pwd",role=UserRole.INTERN)
        self.bu=BusinessUnit.objects.create(name="Projects BU",code="PRJ",manager=self.manager)
        self.other_bu=BusinessUnit.objects.create(name="Other Projects BU",code="OPR",manager=self.manager)
        BusinessUnitMembership.objects.create(business_unit=self.bu,user=self.supervisor)
        BusinessUnitMembership.objects.create(business_unit=self.bu,user=self.employee)
        BusinessUnitMembership.objects.create(business_unit=self.other_bu,user=self.outsider)
        InternProfile.objects.create(user=self.intern,business_unit=self.bu,supervisor=self.supervisor)
        self.payload={"title":"Academy Portal","description":"Delivery project","business_unit":self.bu.id,"supervisor":self.supervisor.id,"assignee_ids":[self.employee.id,self.intern.id],"start_date":"2026-08-01","end_date":"2026-12-01","status":"ACTIVE","progress":10}

    def create_project(self):
        self.client.force_authenticate(self.admin)
        response=self.client.post("/api/projects/",self.payload,format="json")
        self.assertEqual(response.status_code,status.HTTP_201_CREATED,response.data)
        return Project.objects.get()

    def test_super_admin_creates_project_with_employee_and_intern(self):
        project=self.create_project()
        self.assertSetEqual(set(project.assignees.values_list("id",flat=True)),{self.employee.id,self.intern.id})

    def test_supervisor_can_create_own_project_but_cannot_reassign_it(self):
        self.client.force_authenticate(self.supervisor)
        response=self.client.post("/api/projects/",self.payload,format="json")
        self.assertEqual(response.status_code,status.HTTP_201_CREATED,response.data)
        project=Project.objects.get()
        forbidden=self.client.patch(f"/api/projects/{project.id}/",{"business_unit":self.other_bu.id},format="json")
        self.assertEqual(forbidden.status_code,status.HTTP_403_FORBIDDEN)

    def test_hr_cannot_access_projects(self):
        project=self.create_project();self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.get("/api/projects/").status_code,status.HTTP_403_FORBIDDEN)
        response=self.client.patch(f"/api/projects/{project.id}/",{"progress":50},format="json")
        self.assertEqual(response.status_code,status.HTTP_403_FORBIDDEN)

    def test_assignee_and_outsider_visibility_is_scoped(self):
        self.create_project();self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get("/api/projects/").data["count"],1)
        self.client.force_authenticate(self.intern)
        self.assertEqual(self.client.get("/api/projects/").status_code,status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get("/api/projects/").data["count"],0)

    def test_deliverable_workflow_enforces_supervisor_and_participant_fields(self):
        project=self.create_project();self.client.force_authenticate(self.supervisor)
        created=self.client.post("/api/project-deliverables/",{"project":project.id,"title":"Prototype","due_date":"2026-09-01"},format="json")
        self.assertEqual(created.status_code,status.HTTP_201_CREATED)
        deliverable=ProjectDeliverable.objects.get()
        self.client.force_authenticate(self.employee)
        submitted=self.client.patch(f"/api/project-deliverables/{deliverable.id}/",{"status":"SUBMITTED"},format="json")
        self.assertEqual(submitted.status_code,status.HTTP_200_OK)
        forbidden=self.client.patch(f"/api/project-deliverables/{deliverable.id}/",{"title":"Rewritten"},format="json")
        self.assertEqual(forbidden.status_code,status.HTTP_403_FORBIDDEN)

    def test_participants_can_comment_upload_and_download_documents(self):
        project=self.create_project();self.client.force_authenticate(self.employee)
        comment=self.client.post("/api/project-comments/",{"project":project.id,"content":"Première livraison"},format="json")
        self.assertEqual(comment.status_code,status.HTTP_201_CREATED)
        upload=SimpleUploadedFile("deliverable.pdf",b"%PDF-1.4 project",content_type="application/pdf")
        document=self.client.post("/api/project-documents/",{"project":project.id,"file":upload},format="multipart")
        self.assertEqual(document.status_code,status.HTTP_201_CREATED)
        download=self.client.get(f"/api/project-documents/{document.data['id']}/download/")
        self.assertEqual(download.status_code,status.HTTP_200_OK)
        self.assertEqual(ProjectComment.objects.get().author,self.employee)
        self.assertEqual(ProjectDocument.objects.get().uploaded_by,self.employee)

    def test_assignment_rejects_users_outside_business_unit(self):
        self.payload["assignee_ids"]=[self.outsider.id]
        self.client.force_authenticate(self.admin)
        response=self.client.post("/api/projects/",self.payload,format="json")
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)
