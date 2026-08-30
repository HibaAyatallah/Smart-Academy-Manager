from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("business_units", "0013_alter_businessunit_code"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="businessunitmembership",
            name="unique_active_bu_membership",
        ),
        migrations.AddField(
            model_name="businessunitmembership",
            name="active_uniqueness_key",
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Case(
                    models.When(is_active=True, then=models.Value(1)),
                    default=models.Value(None),
                ),
                output_field=models.IntegerField(null=True),
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunitmembership",
            constraint=models.UniqueConstraint(
                fields=("business_unit", "user", "active_uniqueness_key"),
                name="unique_active_bu_membership",
            ),
        ),
    ]
