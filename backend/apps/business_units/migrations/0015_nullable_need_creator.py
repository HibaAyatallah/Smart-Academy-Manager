from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("business_units", "0014_mysql_portable_active_membership_constraint"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AlterField(
            model_name="businessunitneed", name="created_by",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_bu_needs", to=settings.AUTH_USER_MODEL, verbose_name="Créé par"),
        ),
    ]
