# Generated by Django 4.1.8 on 2024-07-24 22:51

from django.apps import apps
from django.db import migrations
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from app.models import (
    User,
    Address,
    AddressRD,
    Household,
    HouseholdMembers,
    EligibilityProgram,
    EligibilityProgramRD,
    IQProgram,
    IQProgramRD,
    Feedback,
    AppAdmin,
)

def create_new_permissions(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None


def apply_admin_group(apps, schema_editor):
    # Define the auth group. Note that this migration will override the
    # permissions if a group exists with this name
    admin_group, _ = Group.objects.get_or_create(name='admin_program')

    # Define the list of permissions (based on testing)
    permissions_list = [
        Permission.objects.get(
            codename='change_user',
            content_type=ContentType.objects.get_for_model(User),
        ),
        Permission.objects.get(
            codename='view_user',
            content_type=ContentType.objects.get_for_model(User),
        ),
        Permission.objects.get(
            codename='view_appadmin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='change_appadmin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='view_address',
            content_type=ContentType.objects.get_for_model(Address),
        ),
        Permission.objects.get(
            codename='change_addressrd',
            content_type=ContentType.objects.get_for_model(AddressRD),
        ),
        Permission.objects.get(
            codename='view_addressrd',
            content_type=ContentType.objects.get_for_model(AddressRD),
        ),
        Permission.objects.get(
            codename='change_household',
            content_type=ContentType.objects.get_for_model(Household),
        ),
        Permission.objects.get(
            codename='view_household',
            content_type=ContentType.objects.get_for_model(Household),
        ),
        Permission.objects.get(
            codename='view_householdmembers',
            content_type=ContentType.objects.get_for_model(HouseholdMembers),
        ),
        Permission.objects.get(
            codename='change_eligibilityprogram',
            content_type=ContentType.objects.get_for_model(EligibilityProgram),
        ),
        Permission.objects.get(
            codename='view_eligibilityprogram',
            content_type=ContentType.objects.get_for_model(EligibilityProgram),
        ),
        Permission.objects.get(
            codename='add_eligibilityprogramrd',
            content_type=ContentType.objects.get_for_model(EligibilityProgramRD),
        ),
        Permission.objects.get(
            codename='change_eligibilityprogramrd',
            content_type=ContentType.objects.get_for_model(EligibilityProgramRD),
        ),
        Permission.objects.get(
            codename='view_eligibilityprogramrd',
            content_type=ContentType.objects.get_for_model(EligibilityProgramRD),
        ),
        Permission.objects.get(
            codename='view_iqprogram',
            content_type=ContentType.objects.get_for_model(IQProgram),
        ),
        Permission.objects.get(
            codename='add_iqprogramrd',
            content_type=ContentType.objects.get_for_model(IQProgramRD),
        ),
        Permission.objects.get(
            codename='change_iqprogramrd',
            content_type=ContentType.objects.get_for_model(IQProgramRD),
        ),
        Permission.objects.get(
            codename='view_iqprogramrd',
            content_type=ContentType.objects.get_for_model(IQProgramRD),
        ),
        Permission.objects.get(
            codename='view_feedback',
            content_type=ContentType.objects.get_for_model(Feedback),
        ),
        Permission.objects.get(
            codename='delete_eligibilityprogram',
            content_type=ContentType.objects.get_for_model(EligibilityProgram),
        ),
    ]

    # Set the permissions for the group
    admin_group.permissions.set(permissions_list)


def apply_income_group(apps, schema_editor):
    # Define the auth group. Note that this migration will override the
    # permissions if a group exists with this name
    income_group, _ = Group.objects.get_or_create(name='income_verification_staff')

    # Define the list of permissions (from testing)
    permissions_list = [
        Permission.objects.get(
            codename='change_user',
            content_type=ContentType.objects.get_for_model(User),
        ),
        Permission.objects.get(
            codename='view_user',
            content_type=ContentType.objects.get_for_model(User),
        ),
        Permission.objects.get(
            codename='view_appadmin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='change_appadmin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='view_address',
            content_type=ContentType.objects.get_for_model(Address),
        ),
        Permission.objects.get(
            codename='change_addressrd',
            content_type=ContentType.objects.get_for_model(AddressRD),
        ),
        Permission.objects.get(
            codename='view_addressrd',
            content_type=ContentType.objects.get_for_model(AddressRD),
        ),
        Permission.objects.get(
            codename='view_eligibilityprogram',
            content_type=ContentType.objects.get_for_model(EligibilityProgram),
        ),
        Permission.objects.get(
            codename='change_household',
            content_type=ContentType.objects.get_for_model(Household),
        ),
        Permission.objects.get(
            codename='view_household',
            content_type=ContentType.objects.get_for_model(Household),
        ),
        Permission.objects.get(
            codename='view_householdmembers',
            content_type=ContentType.objects.get_for_model(HouseholdMembers),
        ),
        Permission.objects.get(
            codename='view_iqprogram',
            content_type=ContentType.objects.get_for_model(IQProgram),
        ),
    ]

    # Set the permissions for the group
    income_group.permissions.set(permissions_list)


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0036_rename_admin_appadmin"),
    ]

    operations = [
        # Define no operation for reversion. Removing permissions groups will
        # reset all applied users, so the 'apply' procedures instead overwrite
        # permissions on any existing groups
        migrations.RunPython(create_new_permissions, migrations.RunPython.noop),
        migrations.RunPython(apply_admin_group, migrations.RunPython.noop),
        migrations.RunPython(apply_income_group, migrations.RunPython.noop),
    ]
