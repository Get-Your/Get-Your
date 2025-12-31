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
from django.utils.translation import gettext_lazy as _

from app.models import TimeStampedModel


class Address(TimeStampedModel):
    address1 = models.CharField(
        max_length=200,
        default="",
        verbose_name="street address",
        help_text=_(
            "House number and street name.",
        ),
    )
    address2 = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="apt, suite, etc.",
        help_text=_(
            "Leave blank if not applicable.",
        ),
    )

    # Try to get past the things that should be the same for every applicant
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=2, default="")

    zip_code = models.DecimalField(max_digits=5, decimal_places=0)

    is_in_gma = models.BooleanField(null=True, default=None)
    is_city_covered = models.BooleanField(
        null=True,
        default=None,
        help_text=_(
            "Designates whether an address is eligible for benefits. "
            "This can be altered by administrators if the address is outside the GMA.",
        ),
    )
    has_connexion = models.BooleanField(null=True, default=None)
    is_verified = models.BooleanField(default=False)
    address_sha1 = models.CharField(max_length=40, unique=True)

    class Meta:
        verbose_name = "address"
        verbose_name_plural = "addresses"

    def clean(self):
        self.address1 = self.address1.upper()
        self.address2 = self.address2.upper()
        self.city = self.city.upper()
        self.state = self.state.upper()

        # Hash the address with SHA-1 (to guarantee uniqueness)
        keyList = ["address1", "address2", "city", "state", "zip_code"]
        self.address_sha1 = self.hash_address(
            {key: getattr(self, key) for key in keyList},
        )

        return self

    @staticmethod
    def hash_address(address_dict: dict) -> str:
        """
        Create a SHA-1 hash from existing address values.
        :param address_dict: Dictionary of user-entered address fields.
        :returns str: String representation of SHA-1 address hash. SHA-1 hash is
            160 bits; written as hex for 40 characters.
        """
        # Explicitly define address field order
        keyList = ["address1", "address2", "city", "state", "zip_code"]
        # Concatenate string representations of each value in sequence.
        # If value is string, convert to uppercase; if key DNE, use blank string.
        concatVals = "".join(
            [
                address_dict[key].upper()
                if key in address_dict and isinstance(address_dict[key], str)
                else str(address_dict[key])
                if key in address_dict
                else ""
                for key in keyList
            ],
        )
        # Return SHA-1 hash of the concatenated strings
        return hashlib.sha1(bytearray(concatVals, "utf8")).hexdigest()


class IQProgram(TimeStampedModel):
    # ``id`` is the implicity primary key
    program_name = models.CharField(
        max_length=40,
        unique=True,
        help_text=_(
            "Program reference name within the platform. "
            "Must be lowercase with no spaces.",
        ),
    )

    # Store the AMI for which users must be below in order to be eligible
    ami_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text=_(
            "Income threshold of the program, as a fraction of AMI "
            "(e.g. '0.30' == 30% of AMI).",
        ),
    )

    # The following "friendly" fields will be viewable by users. None of them
    # have a database-constrained length in order to maximize flexibility.

    # TODO: remove the max_length input once updated to Django 4.1. In current
    # Django version, max_length=None (the default) throws an exception but is
    # fixed in 4.1 to associate with VARCHAR(MAX).
    # max_length is currently set to a large value, but below Postgres's
    # VARCHAR(MAX).

    # Name of the program
    friendly_name = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly name of the program. "
            "This will be visible to users on the platform.",
        ),
    )
    # Program category (as defined by the Program Lead)
    friendly_category = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly category this program is in. "
            "This will be visible to users on the platform.",
        ),
    )
    # Description of the program
    friendly_description = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly description of the program. "
            "This will be visible to users on the platform.",
        ),
    )
    # Supplemental information about the program (recommend leaving blank
    # (``''``) unless further info is necessary)
    friendly_supplemental_info = models.CharField(
        max_length=5000,
        help_text=_(
            "Any supplemental information to display to the user.",
        ),
    )
    # Hyperlink to learn more about the program
    learn_more_link = models.CharField(
        max_length=5000,
        help_text=_(
            "Link for the user to learn more about the program. "
            "Note that this must start with 'https://' or 'http://'.",
        ),
    )
    # Estimated time period for the eligibility review (in readable text, e.g.
    # 'Two Weeks'). This should be manually updated periodically based on
    # program metrics.
    friendly_eligibility_review_period = models.CharField(
        max_length=5000,
        help_text=_(
            "The estimated time it will take to review a user's application. "
            "This will be visible to users on the platform.",
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Designates whether the program is in-use or not. "
            "Unselect this instead of deleting programs.",
        ),
    )

    # Enable auto-apply for the designated program
    enable_autoapply = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the program should automatically apply new users who are eligible.",
        ),
    )

    # All fields beginning with `requires_` are Boolean and specify whether the
    # matching field in AddressRD is a filter for the program. See
    # backend.get_eligible_iq_programs() for more detail
    requires_is_in_gma = models.BooleanField(
        # Default to True for safety
        default=True,
        help_text=_(
            "Designates whether the user's eligibility address is required to be in the GMA to be eligible.",
        ),
    )
    requires_is_city_covered = models.BooleanField(
        # Default to True for safety
        default=True,
        help_text=_(
            "Designates whether the user's eligibility address is required to be 'covered by the City' to be eligible. "
            "'City coverage' is always True for addresses within the GMA, otherwise it's determined by the Get FoCo administrators.",
        ),
    )
    # The frequency at which an IQ program needs to be renewed. If null, the
    # IQ program is considered to be a lifetime enrollment. Measured in years
    renewal_interval_year = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="renewal interval in years",
        help_text=_(
            "The frequency at which a user needs to renew their application for this IQ program. "
            "Leave blank for a non-renewing (lifetime-enrollment) program.",
        ),
    )

    # Define a link to an external form the user will fill out after applying
    # via Get FoCo. This is used when the program needs more information than
    # collected by Get FoCo (such as number of pets for assistance with pet
    # licensing). If unused, this should be left as blank
    additional_external_form_link = models.CharField(
        max_length=5000,
        blank=True,
        help_text=_(
            "Link to an external form for additional information needed by the program, if applicable (leave blank for no form). "
            "Note that this must start with 'https://' or 'http://', and the target form needs to have a way for the program coordinator to link its information to the Get FoCo user.",
        ),
    )

    class Meta:
        verbose_name = "IQ program"
        verbose_name_plural = "IQ programs"

    def __str__(self):
        return str(self.friendly_name)


class EligibilityProgram(TimeStampedModel):
    """
    Model class to store the eligibility programs.
    """

    # ``id`` is the implicit primary key
    program_name = models.CharField(
        max_length=40,
        unique=True,
        help_text=_(
            "Program reference name within the platform. "
            "Must be lowercase with no spaces.",
        ),
    )

    # Store the AMI threshold that the users with each program are underneath
    ami_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text=_(
            "Income threshold of the program, as a fraction of AMI "
            "(e.g. '0.30' == 30% of AMI)",
        ),
    )

    # This is the friendly name displayed to the user

    # TODO: remove the max_length input once updated to Django 4.1. In current
    # Django version, max_length=None (the default) throws an exception but is
    # fixed in 4.1 to associate with VARCHAR(MAX).
    # max_length is currently set to a large value, but below Postgres's
    # VARCHAR(MAX).

    friendly_name = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly name of the program. "
            "This will be visible to users on the platform.",
        ),
    )
    friendly_description = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly description of the program. "
            "This will be visible to users on the platform.",
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Designates whether the program is in-use or not. "
            "Unselect this instead of deleting programs.",
        ),
    )

    class Meta:
        verbose_name = "eligibility program"
        verbose_name_plural = "eligibility programs"

    def __str__(self):
        return str(self.friendly_name)


class ApplicationPage(TimeStampedModel):
    """
    Storage for each page in the application itself. This is used to track user
    progress through the application (both initial and renewal).

    """

    page_order = models.IntegerField(
        verbose_name="order of page in the application",
        help_text=_(
            "Definition of the order each page appears in the application.",
        ),
    )
    page_url = models.CharField(
        max_length=80,
        verbose_name="django URL for the page",
        help_text=_(
            "The URL of the page, in Django terminology.",
        ),
    )
