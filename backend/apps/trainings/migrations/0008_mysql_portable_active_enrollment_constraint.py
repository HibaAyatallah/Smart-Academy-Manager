from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trainings", "0007_seed_internal_trainings"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="trainingenrollment",
            name="unique_active_enrollment",
        ),
        migrations.AddField(
            model_name="trainingenrollment",
            name="active_uniqueness_key",
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Case(
                    models.When(
                        status__in=[
                            "REJECTED_BY_MANAGER",
                            "REJECTED_BY_SUPER_ADMIN",
                            "CANCELLED",
                        ],
                        then=models.Value(None),
                    ),
                    default=models.Value(1),
                ),
                output_field=models.IntegerField(null=True),
            ),
        ),
        migrations.AddConstraint(
            model_name="trainingenrollment",
            constraint=models.UniqueConstraint(
                fields=("user", "session", "active_uniqueness_key"),
                name="unique_active_enrollment",
            ),
        ),
    ]
