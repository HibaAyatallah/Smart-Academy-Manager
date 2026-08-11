from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assistant", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="chatmessage", name="sources",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="chatmessage", name="request_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
