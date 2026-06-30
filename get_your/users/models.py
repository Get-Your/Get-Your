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

from typing import ClassVar

from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_case_insensitive_field import CaseInsensitiveFieldMixin
from phonenumber_field.modelfields import PhoneNumberField

from app.constants import duration_at_address_choices
from app.constants import rent_own_choices

from .managers import UserManager


class CIEmailField(CaseInsensitiveFieldMixin, models.EmailField):
    """Extend EmailField to be case-insensitive."""

    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveFieldMixin, self).__init__(*args, **kwargs)


class User(AbstractUser):
    """
    Default custom user model for Get-Your.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    # name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = models.CharField(_("first name"), max_length=255)
    last_name = models.CharField(_("last name"), max_length=255)
    email = models.EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    phone_number = PhoneNumberField()
    has_viewed_dashboard = models.BooleanField(default=False, db_default=False)
    is_archived = models.BooleanField(
        default=False,
        db_default=False,
        help_text=_(
            "Designates whether the user is marked as 'archived'.",
        ),
    )
    last_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "The latest time the user completed an application/renewal.",
        ),
    )

    # Define user-updated data
    user_has_updated = models.BooleanField(default=False, db_default=False)
    user_completed_pages = models.ManyToManyField(
        "ref.ApplicationPage",
        related_name="user",
    )

    # Define system-updated data
    last_action_notification_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last user action notification",
        help_text=_(
            "The latest time a notification was sent because of or requesting user action.",
        ),
    )

    # Address-specific fields

    mailing_address = models.ForeignKey(
        "ref.AddressRef",
        # TODO: Consider switching this back to non-nullable (after the
        # transition to v10)
        null=True,
        on_delete=models.DO_NOTHING,  # don't remove this value if address is deleted
        related_name="+",  # don't relate "ref.AddressRef" with this field
    )
    # Note that 'user_has_updated' doesn't apply to the eligibility_address;
    # this is only changed after the initial application during renewals
    eligibility_address = models.ForeignKey(
        "ref.AddressRef",
        # TODO: Consider switching this back to non-nullable (after the
        # transition to v10)
        null=True,
        on_delete=models.DO_NOTHING,  # don't remove this value if address is deleted
        related_name="eligibility_user",
    )

    # Household-specific fields

    is_income_verified = models.BooleanField(
        default=False,
        db_default=False,
        verbose_name="income has been verified",
        help_text=_(
            "Designates whether an applicant has had their income verified.",
        ),
    )
    duration_at_address = models.CharField(
        # TODO: Consider removing the default again (after the transition to v10)
        default="",
        db_default="",
        max_length=200,
        choices=duration_at_address_choices,
    )

    # Define the min and max Gross Annual Household Income as a fraction of
    # AMI (which is a function of number of individuals in household)
    income_as_fraction_of_ami = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        default=None,
    )
    rent_own = models.CharField(
        # TODO: Consider removing the default again (after the transition to v10)
        default="",
        db_default="",
        max_length=200,
        choices=rent_own_choices,
        verbose_name="rent or own",
        help_text=_(
            "Designates whether the applicant rents or owns their primary residence.",
        ),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def are_addresses_the_same(self):
        if self.eligibility_address == self.mailing_address:
            return True

        return False

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    @property
    @admin.display
    def full_name(self):
        """Display 'full name' in the admin portal."""
        return self.first_name + " " + self.last_name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="user_email_ci_uniqueness",
            ),
        ]


class UserNote(models.Model):
    """Internal notes regarding user objects."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="usernotes",
        primary_key=True,  # set this to the primary key of this model
    )

    awaiting_user_response = models.BooleanField(
        default=False,
        db_default=False,
        help_text=_(
            "Designates that the admin is waiting for a user to respond to a request made separate from this platform. "
            "This is used only to filter income-verification applicants.",
        ),
    )

    internal_notes = models.TextField(
        blank=True,
        help_text=_(
            "Notes pertaining to this user, for internal use. "
            "This field is not visible to applicants.",
        ),
    )

    class Meta:
        verbose_name = "user note"
        verbose_name_plural = "user notes"
