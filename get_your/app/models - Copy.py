"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import hashlib

from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Value
from django.db.models.functions import Concat

from app.constants import (
    rent_own_choices,
    duration_at_address_choices,
    platform_settings_render_variables,
    platform_settings_render_variables,
)


# Create custom user manager class (because django only likes to use usernames as usernames not email)
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):

        # Create and save a SuperUser with the given email and password.

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)








class PlatformSettings(models.Model):
    """
    A model for universal platform settings that can be updated via the admin
    portal.
    
    """
    name = models.CharField(
        max_length=20,
        default="",
        # This is included explicitly because it's hardcoded like this in the
        # platform_settings_render_variables
        verbose_name="Name",
        help_text=_(
            "The universal name of the platform (e.g. Get FoCo), to be used in various places."
        ),
    )

    organization = models.CharField(
        max_length=40,
        default="",
        # This is included explicitly because it's hardcoded like this in the
        # platform_settings_render_variables
        verbose_name="Organization",
        help_text=_(
            "The governing organization for the platform (e.g. City of Fort Collins)."
        ),
    )

    phonenumber = PhoneNumberField(
        blank=True,
        # This is included explicitly because it's hardcoded like this in the
        # platform_settings_render_variables
        verbose_name="Phone number",
        help_text=_(
            "The phone number users can call to contact support for the platform (if applicable)."
        ),
    )

    email = models.CharField(
        max_length=50,
        default="",
        # This is included explicitly because it's hardcoded like this in the
        # platform_settings_render_variables
        verbose_name="Email",
        help_text=_(
            "The email address for users to contact platform support."
        ),
    )

    vendor_privacy_policy = models.TextField(
        default='By selecting "Accept" below, you understand the <platform organization> and <platform name> will share basic contact information with <vendor name> in order to register you for this program',
        help_text=_(
            "A general privacy policy that will govern any external vendor that administers a program (when a program uses an external vendor). "
            "Note that variables are case-insensitive and must be added as '<variable name>' (sans quotes) to be rendered as that value on the site. "
            "Only the following are available for use: '<{alw}>'.".format(
                alw=">', '<".join([x for x in platform_settings_render_variables])
            )
        ),
    )

    required_renewal_text = models.TextField(
        max_length=200,
        default="In order to continue providing benefits, we need you to renew your information. Please select 'renew' to start the process.",
        verbose_name="Text for required renewal popup",
        help_text=_(
            "Text that will be displayed when a user is notified they need to complete a renewal to continue receiving benefits."
        ),
    )

    renew_now_text = models.TextField(
        max_length=200,
        default="Renewing now may impact your benefits. Are you sure you want to renew now?",
        verbose_name="Text for 'renew now' popup",
        help_text=_(
            "Text that will be displayed when a user selects the (optional) 'Renew Now' button."
        ),
    )

    dashboard_welcome_text = models.TextField(
        max_length=500,
        default="Congrats on creating an account!\n\nWith the information you provided we gathered all your available programs! All you need to do now is to select Apply Now to apply for programs you're interested in. If you don't see a program you're expecting or are having an issue, please call <contact_number>.",
        verbose_name="Text for dashboard welcome popup",
        help_text=_(
            "Text that will be displayed as a popup when a user reaches the dashboard for the first time. "
            "Note that variables must be added as '<variable_name>' (sans quotes) to be rendered as that value on the site. "
            "Only the following are available for use: '<{alw}>'.".format(
                alw=">', '<".join([x for x in platform_settings_render_variables])
            )
        ),
    )

    feedback_rating_text = 

    feedback_dialog_text = 


#     CONTINUE HERE



    class Meta:
        verbose_name = verbose_name_plural = 'platform settings'
