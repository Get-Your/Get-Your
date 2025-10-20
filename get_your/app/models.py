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

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from files.backend import userfiles_path

from .constants import duration_at_address_choices
from .constants import rent_own_choices

# Get the user model
User = get_user_model()


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides auto-updating ``created_at`` and
    ``modified_at`` fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class IQProgramModel(models.Model):
    """
    An abstract base class model that provides auto-updating ``applied_at`` and
    ``enrolled_at`` fields.
    """

    applied_at = models.DateTimeField(auto_now_add=True)
    enrolled_at = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class Address(TimeStampedModel):
    # Default relation is the User primary key
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,  # set this to the primary key of this model
    )
    mailing_address = models.ForeignKey(
        "ref.Address",
        on_delete=models.DO_NOTHING,  # don't remove this value if address is deleted
        related_name="+",  # don't relate "ref.Address" with this field
    )
    eligibility_address = models.ForeignKey(
        "ref.Address",
        on_delete=models.DO_NOTHING,  # don't remove this value if address is deleted
        related_name="eligibility_user",
    )

    # Important: for this model, ``user_has_updated`` applies *only to the mailing address*
    user_has_updated = models.BooleanField(default=False)

    class Meta:
        verbose_name = "address"
        verbose_name_plural = "addresses"


class Household(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    user_has_updated = models.BooleanField(default=False)
    is_income_verified = models.BooleanField(
        default=False,
        verbose_name="income has been verified",
        help_text=_(
            "Designates whether an applicant has had their income verified.",
        ),
    )
    duration_at_address = models.CharField(
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
        max_length=200,
        choices=rent_own_choices,
        verbose_name="rent or own",
        help_text=_(
            "Designates whether the applicant rents or owns their primary residence.",
        ),
    )

    class Meta:
        verbose_name = "household"
        verbose_name_plural = "household"


class HouseholdMembers(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    full_name = models.CharField(max_length=200)
    birthdate = models.DateField()
    identification_path = models.FileField()

    user_has_updated = models.BooleanField(default=False)

    class Meta:
        verbose_name = "household member"
        verbose_name_plural = "household members"


class IQProgram(IQProgramModel):
    """Model class to store each user's program enrollment status.

    Note that the record for a program is created when a user applies (at which
    point ``applied_at`` is timestamped) and ``is_enrolled`` is set to ``True``
    and ``enrolled_at`` is timestamped when income verification is complete.

    """

    # ``id`` is the implicit primary key
    user = models.ForeignKey(
        User,
        related_name="iq_programs",
        on_delete=models.CASCADE,
    )

    program = models.ForeignKey(
        "ref.IQProgram",
        related_name="iq_programs",
        on_delete=models.DO_NOTHING,  # don't update these values if the program is deleted
    )

    is_enrolled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "user IQ program"
        verbose_name_plural = "user IQ programs"


class EligibilityProgram(TimeStampedModel):
    """
    Model class to store the eligibility programs.
    """

    # ``id`` is the implicit primary key
    user = models.ForeignKey(
        User,
        related_name="eligibility_files",
        on_delete=models.CASCADE,
    )

    program = models.ForeignKey(
        "ref.EligibilityProgram",
        # Prevent deletion of the referenced object (under restricted conditions)
        # (ref https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.ForeignKey.on_delete)
        on_delete=models.RESTRICT,
    )

    # Upload the file(?) to the proper directory in Azure Blob Storage and store
    # the path
    document_path = models.FileField(
        max_length=5000,
        upload_to=userfiles_path,
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = "user eligibility program"
        verbose_name_plural = "user eligibility programs"
