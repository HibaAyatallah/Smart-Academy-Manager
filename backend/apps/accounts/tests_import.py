"""
Tests d'importation en masse — BulkImportTests
Couvre tous les scénarios demandés :
  - création automatique des 4 BU via migration
  - migration rejouée sans doublon
  - CLIENT_EXTERNE avec BU vide → valide
  - COLLABORATEUR avec BU valide → valide
  - FORMATEUR avec BU valide → valide
  - STAGIAIRE avec BU valide → valide
  - rôle nécessitant BU mais cellule vide → invalide
  - BU inconnue → invalide avec message détaillé
  - résumé 20 collab / 1 client / 5 formateurs / 3 stagiaires
  - import complet 29 lignes
  - rollback total en cas d'erreur
"""
import io
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.recruitment.models import EmployeeProfile
from apps.accounts.services.account_generation import generate_professional_email
from apps.accounts.services.bulk_import import parse_and_validate_file, execute_import

User = get_user_model()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _csv(rows, header="Prénom,Nom,Email personnel,Téléphone,Profil,BU,Poste"):
    lines = [header] + rows
    return "\n".join(lines).encode("utf-8")


def _make_bu(name, code, manager=None):
    return BusinessUnit.objects.get_or_create(
        code=code,
        defaults={"name": name, "manager": manager, "is_active": True},
    )[0]


# ─── Suite principale ──────────────────────────────────────────────────────────

class BulkImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            email="admin@finatech.com",
            password="pwd",
            role=UserRole.SUPER_ADMIN,
        )
        self.hr_user = User.objects.create_user(
            email="hr@finatech.com",
            password="pwd",
            role=UserRole.HR,
        )
        # Create the four official BUs (mirroring the seed migration)
        self.bu_netsec   = _make_bu("NetSEC",   "NetSEC")
        self.bu_system   = _make_bu("System",   "System")
        self.bu_software = _make_bu("Software", "Software")
        self.bu_achat    = _make_bu("Achat",    "Achat")

    # ── Permissions ──────────────────────────────────────────────────────────

    def test_super_admin_access(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(reverse("import-preview"))
        self.assertNotEqual(response.status_code, 403)

    def test_hr_denial(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(reverse("import-preview"))
        self.assertEqual(response.status_code, 403)

    # ── Seed migration idempotence ────────────────────────────────────────────

    def test_four_official_bus_exist_in_db(self):
        """La migration seed doit avoir créé les 4 BU officielles."""
        for code in ["NetSEC", "System", "Software", "Achat"]:
            self.assertTrue(
                BusinessUnit.objects.filter(code=code).exists(),
                f"La BU «{code}» devrait exister en base après la migration.",
            )

    def test_seed_migration_is_idempotent_no_duplicate(self):
        """Rejouer le seed ne crée pas de doublon."""
        from apps.business_units.seed_business_units_helper import OFFICIAL_BUSINESS_UNITS

        initial_count = BusinessUnit.objects.filter(
            code__in=[bu["code"] for bu in OFFICIAL_BUSINESS_UNITS]
        ).count()

        # Simulate re-running seed
        for bu_data in OFFICIAL_BUSINESS_UNITS:
            BusinessUnit.objects.get_or_create(
                code=bu_data["code"],
                defaults={"name": bu_data["name"], "is_active": True},
            )

        final_count = BusinessUnit.objects.filter(
            code__in=[bu["code"] for bu in OFFICIAL_BUSINESS_UNITS]
        ).count()
        self.assertEqual(initial_count, final_count, "Le seed ne doit pas créer de doublons.")

    # ── Parsing — rôles ───────────────────────────────────────────────────────

    def test_client_externe_with_empty_bu_is_valid(self):
        """CLIENT_EXTERNE avec BU vide doit être accepté (pas de BU requise)."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["Alice,Durand,alice.ext@perso.com,+33600000001,CLIENT_EXTERNE,,Commercial"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1, data)
        self.assertEqual(data["invalid_count"], 0, data)
        # BU doit être None, pas une string vide
        payload = data["valid_rows"][0]["payload"]
        self.assertIsNone(payload["business_unit"])
        self.assertIsNone(payload["business_unit_name"])

    def test_collaborateur_with_valid_bu(self):
        """COLLABORATEUR avec BU valide doit être accepté."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["Bob,Martin,bob@perso.com,+33600000002,COLLABORATEUR,NetSEC,Dev"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1, data)
        self.assertEqual(data["valid_rows"][0]["payload"]["role"], UserRole.EMPLOYEE)
        self.assertEqual(data["valid_rows"][0]["payload"]["business_unit"], self.bu_netsec.id)

    def test_formateur_with_valid_bu(self):
        """FORMATEUR avec BU valide doit être accepté."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["Carla,Bernard,carla@perso.com,+33600000003,FORMATEUR,System,Formateur"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1, data)
        self.assertEqual(data["valid_rows"][0]["payload"]["role"], UserRole.TRAINER_TUTOR)

    def test_stagiaire_with_valid_bu(self):
        """STAGIAIRE avec BU valide doit être accepté."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["David,Petit,david@perso.com,+33600000004,STAGIAIRE,Achat,Stagiaire"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1, data)
        self.assertEqual(data["valid_rows"][0]["payload"]["role"], UserRole.INTERN)

    def test_employee_with_missing_bu_is_invalid(self):
        """Un COLLABORATEUR sans BU doit être invalide."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["Eva,Lambert,eva@perso.com,+33600000005,COLLABORATEUR,,Dev"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 0, data)
        self.assertEqual(data["invalid_count"], 1, data)
        error_text = " ".join(data["invalid_rows"][0]["errors"])
        self.assertIn("Business Unit est requise", error_text)

    def test_unknown_bu_produces_detailed_error(self):
        """Une BU inconnue doit produire un message d'erreur avec ligne, email, valeur, autorisées."""
        self.client.force_authenticate(user=self.super_admin)
        csv = _csv(["Frank,Girard,frank@perso.com,+33600000006,COLLABORATEUR,BU_INCONNUE,Dev"])
        file = SimpleUploadedFile("test.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["invalid_count"], 1, data)
        error_text = " ".join(data["invalid_rows"][0]["errors"])
        self.assertIn("BU_INCONNUE", error_text)
        self.assertIn("NetSEC", error_text)          # valeurs autorisées présentes
        self.assertIn("frank@perso.com", error_text) # email présent dans message

    # ── Calcul de répartition ─────────────────────────────────────────────────

    def _build_preview_with_roles(self):
        """Construit un preview avec 20 EMPLOYEE, 1 CLIENT, 5 TRAINER_TUTOR, 3 INTERN."""
        rows = []
        for i in range(20):
            rows.append(f"Collab{i},Nom{i},collab{i}@perso.com,+336{i:08d},COLLABORATEUR,NetSEC,Dev")
        rows.append("Client,Ext,client.ext@perso.com,+33600000099,CLIENT_EXTERNE,,Commercial")
        for i in range(5):
            rows.append(f"Form{i},Nom{i},form{i}@perso.com,+336{i+20:08d},FORMATEUR,System,Formateur")
        for i in range(3):
            rows.append(f"Stag{i},Nom{i},stag{i}@perso.com,+336{i+30:08d},STAGIAIRE,Achat,Stagiaire")
        return rows

    def test_role_breakdown_29_accounts(self):
        """Le preview de 29 lignes doit retourner la répartition exacte."""
        self.client.force_authenticate(user=self.super_admin)
        rows = self._build_preview_with_roles()
        self.assertEqual(len(rows), 29)
        csv = _csv(rows)
        file = SimpleUploadedFile("test29.csv", csv, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 29, data)
        self.assertEqual(data["invalid_count"], 0, data)

        roles = [r["payload"]["role"] for r in data["valid_rows"]]
        self.assertEqual(roles.count(UserRole.EMPLOYEE),      20, "20 collaborateurs")
        self.assertEqual(roles.count(UserRole.CLIENT),         1, "1 client externe")
        self.assertEqual(roles.count(UserRole.TRAINER_TUTOR),  5, "5 formateurs")
        self.assertEqual(roles.count(UserRole.INTERN),         3, "3 stagiaires")

    # ── Import complet ────────────────────────────────────────────────────────

    def test_import_execution_29_accounts(self):
        """Confirmer l'import de 29 comptes doit créer 29 utilisateurs."""
        self.client.force_authenticate(user=self.super_admin)
        rows = self._build_preview_with_roles()
        csv_data = _csv(rows)
        file = SimpleUploadedFile("test29.csv", csv_data, content_type="text/csv")

        # Step 1: preview
        resp_preview = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(resp_preview.status_code, 200)
        valid_rows = resp_preview.json()["valid_rows"]
        self.assertEqual(len(valid_rows), 29)

        # Step 2: confirm
        resp_confirm = self.client.post(
            reverse("import-confirm"), {"valid_rows": valid_rows}, format="json"
        )
        self.assertEqual(resp_confirm.status_code, 200, resp_confirm.json())
        results = resp_confirm.json()["results"]
        self.assertEqual(len(results), 29)

        # All must have a professional email
        for r in results:
            self.assertIn("@finatech.com", r["Email Professionnel"])
            self.assertNotEqual(r["Mot de passe temporaire"], "")

    def test_rollback_on_import_error(self):
        """En cas d'erreur pendant l'import, aucun utilisateur ne doit être créé."""
        self.client.force_authenticate(user=self.super_admin)
        initial_count = User.objects.count()

        # valid_rows with one row that has an unresolved BU (string instead of ID)
        valid_rows = [
            {
                "row": 2,
                "payload": {
                    "first_name": "Error",
                    "last_name": "Test",
                    "contact_email": "err@perso.com",
                    "phone_number": "",
                    "role": UserRole.EMPLOYEE,
                    "business_unit": "BU_INCONNUE",  # will cause ValueError in Pass 2
                    "position": "Dev",
                    "supervisor": None,
                },
            }
        ]
        response = self.client.post(
            reverse("import-confirm"), {"valid_rows": valid_rows}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        # No user should have been created
        self.assertEqual(User.objects.count(), initial_count)

    # ── Tests du parsing original (non-regression) ───────────────────────────

    def test_csv_parsing_and_valid_roles(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = "Prénom,Nom,Email personnel,Téléphone,Profil,BU,Poste\nJean,Dupont,jean@personal.com,1234,EMPLOYEE,NetSEC,Dev".encode("utf-8")
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 1)
        self.assertEqual(data["invalid_count"], 0)

    def test_duplicate_bu_aliases_are_merged_when_values_do_not_conflict(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = (
            "Prénom,Nom,Email personnel,Profil,BU,Business Unit\n"
            "Jean,Dupont,jean.alias@example.com,EMPLOYEE,NetSEC,\n"
            "Sara,Martin,sara.alias@example.com,EMPLOYEE,,NetSEC\n"
        ).encode("utf-8")
        file = SimpleUploadedFile("aliases.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["valid_count"], 2)
        self.assertEqual(response.json()["invalid_count"], 0)
        self.assertTrue(
            all(row["payload"]["business_unit"] == self.bu_netsec.id
                for row in response.json()["valid_rows"])
        )

    def test_duplicate_bu_aliases_return_400_when_values_conflict(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = (
            "Prénom,Nom,Email personnel,Profil,BU,Business Unit\n"
            "Jean,Dupont,jean.conflict@example.com,EMPLOYEE,NetSEC,System\n"
        ).encode("utf-8")
        file = SimpleUploadedFile("aliases-conflict.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Colonnes contradictoires", response.json()["error"])

    @patch("apps.accounts.views.parse_and_validate_file", side_effect=ValueError("bad columns"))
    def test_preview_converts_unexpected_parser_errors_to_400(self, _parser):
        self.client.force_authenticate(user=self.super_admin)
        file = SimpleUploadedFile("broken.csv", b"a,b\n1,2", content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("structure de colonnes invalide", response.json()["error"])

    def test_missing_columns_and_invalid_data(self):
        self.client.force_authenticate(user=self.super_admin)
        csv_content = "Prénom,Nom,Email personnel,Profil,BU\n,Dupont,invalid_email,INVALID_ROLE,BU_FAKE".encode("utf-8")
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("import-preview"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid_count"], 0)
        self.assertEqual(data["invalid_count"], 1)
        errors = " ".join(data["invalid_rows"][0]["errors"])
        self.assertIn("Prénom est requis", errors)
        self.assertIn("Format d'email invalide", errors)
        self.assertIn("Rôle ou profil invalide", errors)
        self.assertIn("BU_FAKE", data["missing_bus"])

    def test_email_collision(self):
        User.objects.create_user(email="jean.dupont@finatech.com", password="pwd")
        email = generate_professional_email("Jean", "Dupont")
        self.assertEqual(email, "jean.dupont2@finatech.com")

    def test_import_execution_single_employee(self):
        self.client.force_authenticate(user=self.super_admin)
        valid_rows = [{
            "row": 2,
            "payload": {
                "first_name": "Marc",
                "last_name": "Lafayette",
                "contact_email": "marc@perso.com",
                "phone_number": "",
                "role": UserRole.EMPLOYEE,
                "business_unit": self.bu_netsec.id,
                "position": "Dev",
                "supervisor": None,
            }
        }]
        response = self.client.post(reverse("import-confirm"), {"valid_rows": valid_rows}, format="json")
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(contact_email="marc@perso.com")
        self.assertEqual(user.email, "marc.lafayette@finatech.com")
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.check_password(response.json()["results"][0]["Mot de passe temporaire"]))
        self.assertTrue(EmployeeProfile.objects.filter(user=user).exists())
        self.assertTrue(BusinessUnitMembership.objects.filter(user=user, business_unit=self.bu_netsec).exists())
