from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bookings", "0004_cancellation_actor_name_cancellation_source_and_more")]

    operations = [
        migrations.AddField(model_name="booking", name="confirmed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="booking", name="checked_in_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="booking", name="completed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="booking", name="no_show_at", field=models.DateTimeField(blank=True, null=True)),
    ]
