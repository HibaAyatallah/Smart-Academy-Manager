from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def snapshot_candidate_identity(apps, schema_editor):
    CandidateProfile = apps.get_model("recruitment", "CandidateProfile")
    for profile in CandidateProfile.objects.select_related("user").iterator():
        if profile.user_id:
            profile.account_email = profile.user.email
            profile.account_first_name = profile.user.first_name
            profile.account_last_name = profile.user.last_name
            profile.save(update_fields=["account_email", "account_first_name", "account_last_name"])


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0013_applicationmatch_explainable_scoring"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="candidateprofile", name="account_email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="candidateprofile", name="account_first_name", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="candidateprofile", name="account_last_name", field=models.CharField(blank=True, max_length=150)),
        migrations.RunPython(snapshot_candidate_identity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="candidateprofile", name="user",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="candidate_profile", to=settings.AUTH_USER_MODEL),
        ),
    ]
