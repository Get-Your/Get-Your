# Generated by Django 4.1.8 on 2024-01-15 23:30

import pendulum

from django.db import migrations

from django_q.models import Schedule

SCHEDULE_NAME = 'Send Renewal Email'

def apply_migration(apps, schema_editor):
    # Add daily 'Send Renewal Email' schedule to Django-Q2
    Schedule.objects.create(
        # Name the schedule
        name=SCHEDULE_NAME,
        # Run the app.tasks.send_renewal_email function
        func='app.tasks.send_renewal_email',
        # Create a 'daily' schedule
        schedule_type=Schedule.DAILY,
        # Repeat forever
        repeats=-1,
        # Call the cluster specified by the Q_CLUSTER setting
        cluster='DjangORM',
        # Set the next run to be 1 minute after midnight in America/Denver
        # timezone, starting tomorrow (from whenever this is applied)
        next_run=pendulum.today(tz='America/Denver').add(days=1, minutes=1),
    )


def revert_migration(apps, schema_editor):
    # Remove the schedule with the same name
    Schedule.objects.filter(name=SCHEDULE_NAME).delete()

class Migration(migrations.Migration):
    dependencies = [
        (
            "app",
            "0016_rename_renewal_interval_iqprogramrd_renewal_interval_month_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(apply_migration, revert_migration),
    ]