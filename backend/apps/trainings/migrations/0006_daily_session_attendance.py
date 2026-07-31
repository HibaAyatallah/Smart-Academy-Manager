from django.db import migrations, models
import django.db.models.deletion


def set_existing_attendance_dates(apps, schema_editor):
    SessionAttendance = apps.get_model("trainings", "SessionAttendance")
    for attendance in SessionAttendance.objects.select_related("enrollment__session"):
        attendance.date = attendance.enrollment.session.start_date
        attendance.save(update_fields=["date"])


class Migration(migrations.Migration):
    dependencies = [("trainings", "0005_remove_training_moodle_course_id_and_more")]

    operations = [
        migrations.AddField(
            model_name="sessionattendance",
            name="date",
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name="sessionattendance",
            name="enrollment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attendances",
                to="trainings.trainingenrollment",
            ),
        ),
        migrations.RunPython(
            set_existing_attendance_dates,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="sessionattendance",
            name="date",
            field=models.DateField(),
        ),
        migrations.AddConstraint(
            model_name="sessionattendance",
            constraint=models.UniqueConstraint(
                fields=("enrollment", "date"),
                name="unique_daily_attendance_per_enrollment",
            ),
        ),
        migrations.AlterModelOptions(
            name="sessionattendance",
            options={"ordering": ["date", "enrollment__user__email"]},
        ),
    ]
