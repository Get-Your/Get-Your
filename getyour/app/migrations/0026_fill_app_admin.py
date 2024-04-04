# Generated by Django 4.1.8 on 2024-04-04 17:32

from django.db import migrations

from app.models import User, Admin


def apply_migration(apps, schema_editor):
    # Create an Admin object for each User object that already exists. This will
    # be handled on User creation going forward

    Admin.objects.bulk_create(
        [Admin(user=usr) for usr in User.objects.all()],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0025_admin"),
    ]

    operations = [
        # Don't do anything for the reversion
        migrations.RunPython(apply_migration, migrations.RunPython.noop),
    ]
