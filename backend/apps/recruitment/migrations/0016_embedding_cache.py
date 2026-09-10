from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0015_hybrid_matching_foundations")]

    operations = [
        migrations.CreateModel(
            name="EmbeddingCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("representation_hash", models.CharField(max_length=64)),
                ("model_identifier", models.CharField(max_length=180)),
                ("vector", models.JSONField()),
                ("dimensions", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("representation_hash", "model_identifier"),
                        name="unique_recruitment_embedding_cache",
                    )
                ]
            },
        )
    ]
