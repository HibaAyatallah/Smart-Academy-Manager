from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0002_candidateprofile_study_field_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="candidateprofile",
            old_name="education_level",
            new_name="study_level",
        ),
        migrations.AddField(
            model_name="candidateprofile",
            name="study_level_other",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="candidateprofile",
            name="study_level",
            field=models.CharField(
                choices=[
                    ("FIRST_YEAR", "1re annee"),
                    ("SECOND_YEAR", "2e annee"),
                    ("THIRD_YEAR", "3e annee"),
                    ("FOURTH_YEAR", "4e annee"),
                    ("FIFTH_YEAR", "5e annee"),
                    ("BACHELOR", "Licence"),
                    ("MASTER", "Master"),
                    ("ENGINEERING", "Cycle ingenieur"),
                    ("DOCTORATE", "Doctorat"),
                    ("OTHER", "Autre"),
                ],
                max_length=32,
            ),
        ),
    ]

