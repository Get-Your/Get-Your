# Generated by Django 4.1.8 on 2024-07-24 21:22

from django.db import migrations, models
from django.conf import settings
from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
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


# Functions from the following migrations need manual copying.
# Move them and any dependencies into this file, then update the
# RunPython operations to refer to the local versions:
# app.migrations.0035_auto_20240722_1428


def apply_admin_group(apps, schema_editor):
    # Define the auth group. Note that this migration will override the
    # permissions if a group exists with this name
    admin_group, _ = Group.objects.get_or_create(name='admin_program')

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
            codename='view_admin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='change_admin',
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
            codename='view_admin',
            content_type=ContentType.objects.get_for_model(AppAdmin),
        ),
        Permission.objects.get(
            codename='change_admin',
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
            codename='change_eligibilityprogram',
            content_type=ContentType.objects.get_for_model(EligibilityProgram),
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

    replaces = [('app', '0031_merge_20240422_0637'), ('app', '0032_alter_addressrd_address1_alter_addressrd_address2'), ('app', '0033_alter_addressrd_is_city_covered'), ('app', '0034_alter_iqprogramrd_friendly_supplemental_info'), ('app', '0035_auto_20240722_1428')]

    dependencies = [
        ('app', '0020_merge_20240421_0832'),
        ('app', '0020_alter_address_options_alter_addressrd_options_and_more_squashed_0030_alter_permissions_group'),
    ]

    operations = [
        # Define no operation for reversion. Removing permissions groups will
        # reset all applied users, so the 'apply' procedures instead overwrite
        # permissions on any existing groups
        migrations.RunPython(apply_admin_group, migrations.RunPython.noop),
        migrations.RunPython(apply_income_group, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='addressrd',
            name='address1',
            field=models.CharField(default='', help_text='House number and street name.', max_length=200, verbose_name='street address'),
        ),
        migrations.AlterField(
            model_name='addressrd',
            name='address2',
            field=models.CharField(blank=True, default='', help_text='Leave blank if not applicable.', max_length=200, verbose_name='apt, suite, etc.'),
        ),
        migrations.AlterField(
            model_name='addressrd',
            name='is_city_covered',
            field=models.BooleanField(default=None, help_text='Designates whether an address is eligible for benefits. This can be altered by administrators if the address is outside the GMA.', null=True),
        ),
        migrations.AlterField(
            model_name='iqprogramrd',
            name='friendly_supplemental_info',
            field=models.CharField(help_text='Any supplemental information to display to the user.', max_length=5000),
        ),
    ]
