from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0016_embedding_cache")]

    operations = [
        migrations.AddField(
            model_name="cvanalysis",
            name="raw_text",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="CVRAGIndexState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cv_sha256", models.CharField(max_length=64)),
                ("extractor_version", models.CharField(max_length=32)),
                ("rag_index_version", models.CharField(max_length=32)),
                ("embedding_model", models.CharField(max_length=180)),
                ("content_fingerprint", models.CharField(max_length=64)),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("indexed_at", models.DateTimeField(auto_now=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="rag_index_state", to="recruitment.application")),
                ("application_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rag_index_states", to="recruitment.applicationdocument")),
            ],
        ),
    ]
