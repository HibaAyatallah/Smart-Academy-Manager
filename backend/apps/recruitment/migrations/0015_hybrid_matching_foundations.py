from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0014_detach_candidate_account")]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="required_experience_years",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddField(model_name="applicationmatch", name="candidate_fingerprint", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="applicationmatch", name="offer_fingerprint", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="applicationmatch", name="candidate_representation_hash", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="applicationmatch", name="offer_representation_hash", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="applicationmatch", name="semantic_score", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
        migrations.AddField(model_name="applicationmatch", name="semantic_model", field=models.CharField(blank=True, max_length=120)),
    ]
