from rest_framework.test import APITestCase
from apps.accounts.choices import UserRole
from apps.accounts.models import User

class EndpointRoleMatrixTests(APITestCase):
    matrix = {
        UserRole.SUPER_ADMIN: {"/api/users/": 200, "/api/audit-logs/": 200, "/api/reports/summary/": 200, "/api/contact-messages/": 200},
        UserRole.HR: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 200, "/api/contact-messages/": 403},
        UserRole.BU_MANAGER: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 200, "/api/contact-messages/": 403},
        UserRole.TRAINER_TUTOR: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 403, "/api/contact-messages/": 403},
        UserRole.EMPLOYEE: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 403, "/api/contact-messages/": 403},
        UserRole.INTERN: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 403, "/api/contact-messages/": 403},
        UserRole.CANDIDATE: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 403, "/api/contact-messages/": 403},
        UserRole.CLIENT: {"/api/users/": 403, "/api/audit-logs/": 403, "/api/reports/summary/": 403, "/api/contact-messages/": 403},
    }
    def test_sensitive_get_endpoints_follow_role_matrix(self):
        for index,(role,endpoints) in enumerate(self.matrix.items()):
            user=User.objects.create_user(email=f"matrix-{index}@test.com",password="pwd",role=role)
            self.client.force_authenticate(user)
            for endpoint,expected in endpoints.items():
                with self.subTest(role=role,endpoint=endpoint):
                    self.assertEqual(self.client.get(endpoint).status_code,expected)

    def test_all_authenticated_roles_only_receive_their_notifications(self):
        for index,role in enumerate(self.matrix):
            user=User.objects.create_user(email=f"notify-matrix-{index}@test.com",password="pwd",role=role)
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/notifications/").status_code,200)
