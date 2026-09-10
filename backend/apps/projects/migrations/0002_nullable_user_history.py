from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AlterField(
            model_name="project", name="supervisor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="supervised_projects", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="project", name="created_by",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_projects", to=settings.AUTH_USER_MODEL),
        ),
    ]
