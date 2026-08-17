from django.db import migrations, models
import apps.recruitment.models


REQUIRED_DOCUMENTS = (
    ("NATIONAL_ID", "Carte nationale scannée", "Copie lisible de la carte nationale."),
    ("PERSONAL_PHOTO", "Photo personnelle professionnelle", "Photo récente à usage professionnel."),
    ("ANTHROPOMETRIC_RECORD", "Fiche anthropométrique", "Fiche anthropométrique du stagiaire."),
    ("CONVENTION", "Convention de stage", "Convention de stage signée."),
)


def seed_required_documents(apps, schema_editor):
    Requirement = apps.get_model("recruitment", "InternDocumentRequirement")
    for document_type, name, description in REQUIRED_DOCUMENTS:
        requirement = Requirement.objects.filter(document_type=document_type).first()
        if requirement:
            requirement.is_required = True
            requirement.is_active = True
            requirement.save(update_fields=["is_required", "is_active"])
        else:
            Requirement.objects.create(document_type=document_type, name=name, description=description, is_required=True, is_active=True)


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0010_cvanalysis_structured_fields")]
    operations = [
        migrations.AlterField(
            model_name="interndocumentrequirement",
            name="document_type",
            field=models.CharField(choices=[("NATIONAL_ID", "Carte nationale scannée"), ("PERSONAL_PHOTO", "Photo personnelle professionnelle"), ("ANTHROPOMETRIC_RECORD", "Fiche anthropométrique"), ("CONVENTION", "Convention de stage"), ("INSURANCE", "Assurance"), ("SCHOOL_CERT", "Attestation de scolarité"), ("NDA", "Accord de confidentialité"), ("OTHER", "Autre document")], max_length=32),
        ),
        migrations.AlterField(
            model_name="interndocument",
            name="document_type",
            field=models.CharField(choices=[("NATIONAL_ID", "Carte nationale scannée"), ("PERSONAL_PHOTO", "Photo personnelle professionnelle"), ("ANTHROPOMETRIC_RECORD", "Fiche anthropométrique"), ("CONVENTION", "Convention de stage"), ("INSURANCE", "Assurance"), ("SCHOOL_CERT", "Attestation de scolarité"), ("NDA", "Accord de confidentialité"), ("OTHER", "Autre document")], max_length=32),
        ),
        migrations.AlterField(
            model_name="interndocument",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to=apps.recruitment.models.intern_document_upload_to),
        ),
        migrations.AddField(
            model_name="interndocument",
            name="submission_method",
            field=models.CharField(choices=[("ONLINE", "Déposé en ligne"), ("PHYSICAL", "Remis physiquement")], default="ONLINE", max_length=16),
        ),
        migrations.RunPython(seed_required_documents, migrations.RunPython.noop),
    ]
