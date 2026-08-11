"""
Migration de données idempotente : crée les quatre Business Units officielles
(NetSEC, System, Software, Achat) si elles n'existent pas encore.

- Ne dépend PAS d'un Responsable BU existant (manager nullable depuis 0011)
- N'est jamais rejouée (get_or_create garantit l'idempotence)
- Ne crée aucun doublon
- Conserve toutes les relations existantes
"""
from django.db import migrations
from apps.business_units.seed_business_units_helper import OFFICIAL_BUSINESS_UNITS


def seed_business_units(apps, schema_editor):
    BusinessUnit = apps.get_model("business_units", "BusinessUnit")
    created_count = 0
    for bu_data in OFFICIAL_BUSINESS_UNITS:
        obj, created = BusinessUnit.objects.get_or_create(
            code=bu_data["code"],
            defaults={
                "name": bu_data["name"],
                "description": f"Business Unit {bu_data['name']} — créée automatiquement.",
                "is_active": True,
            },
        )
        if created:
            created_count += 1

    if created_count:
        print(f"\n  [OK] {created_count} Business Unit(s) cree(s) : "
              + ", ".join(bu["name"] for bu in OFFICIAL_BUSINESS_UNITS))
    else:
        print("\n  [OK] Les quatre Business Units officielles sont deja presentes.")


def remove_seeded_business_units(apps, schema_editor):
    """
    Reverse migration: supprime uniquement les BU créées par ce seed
    (uniquement si elles n'ont aucun membre, pour ne pas casser les données réelles).
    """
    BusinessUnit = apps.get_model("business_units", "BusinessUnit")
    for bu_data in OFFICIAL_BUSINESS_UNITS:
        BusinessUnit.objects.filter(
            code=bu_data["code"],
            memberships__isnull=True,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business_units", "0011_alter_businessunit_manager_nullable"),
    ]

    operations = [
        migrations.RunPython(
            seed_business_units,
            reverse_code=remove_seeded_business_units,
        ),
    ]
