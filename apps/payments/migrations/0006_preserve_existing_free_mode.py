from django.db import migrations


def preserve_mode(apps, schema_editor):
    policy = apps.get_model('payments', 'PlatformBillingSettings').objects.filter(pk=1).first()
    if policy and policy.paid_mode_enabled:
        apps.get_model('clubs', 'Branch').objects.update(is_free=False)
        apps.get_model('barbers', 'Barber').objects.update(is_free=False)


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0005_independent_barber_billing_and_free_mode'),
        ('clubs', '0022_add_individual_free_mode'),
        ('barbers', '0003_add_individual_free_mode'),
    ]
    operations = [migrations.RunPython(preserve_mode, migrations.RunPython.noop)]
