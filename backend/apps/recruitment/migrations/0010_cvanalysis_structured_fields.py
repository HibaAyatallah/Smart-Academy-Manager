from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recruitment", "0009_trainingrecommendation")]
    operations = [
        migrations.AddField(model_name="cvanalysis", name="full_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="cvanalysis", name="email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="cvanalysis", name="phone", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="cvanalysis", name="location", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="cvanalysis", name="education", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="companies", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="positions", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="languages", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="certifications", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="extraction_warnings", field=models.JSONField(default=list)),
        migrations.AddField(model_name="cvanalysis", name="extraction_method", field=models.CharField(blank=True, max_length=32)),
    ]
