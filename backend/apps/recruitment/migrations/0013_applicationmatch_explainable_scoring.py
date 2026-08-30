from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0012_alter_application_application_type_and_more")]

    operations = [
        migrations.AddField(
            model_name="applicationmatch",
            name="additional_skills",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="applicationmatch",
            name="score_breakdown",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="applicationmatch",
            name="candidate_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="applicationmatch",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
