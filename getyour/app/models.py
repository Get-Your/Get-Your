"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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

from app.constants import rent_own_choices, duration_at_address_choices


def userfiles_path(instance, filename):
    # file will be uploaded to user_<id>/<filename>
    try:
        return f"user_{instance.user_id}/{filename}"
    except AttributeError:
        return f"user_{instance.id}/{filename}"


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


class CaseInsensitiveFieldMixin:
    """
    Field mixin that uses case-insensitive lookup alternatives if they exist.

    This and associate case-insensitive index migration found in
    https://concisecoder.io/2018/10/27/case-insensitive-fields-in-django-models

    """
    LOOKUP_CONVERSIONS = {
        'exact': 'iexact',
        'contains': 'icontains',
        'startswith': 'istartswith',
        'endswith': 'iendswith',
        'regex': 'iregex',
    }

    def get_lookup(self, lookup_name):
        converted = self.LOOKUP_CONVERSIONS.get(lookup_name, lookup_name)
        return super().get_lookup(converted)


# Class to automatically save date data was entered into postgre
class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides selfupdating ``created`` and ``modified`` fields.
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Class to automate generic timestamps in database data
class GenericTimeStampedModel(models.Model):
    """
    An abstract base class model that provides auto-updating ``created_at`` and
    ``modified_at`` fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Class to automate IQ-program-specific timestamps in database data
class IQProgramTimeStampedModel(models.Model):
    """
    An abstract base class model that provides auto-updating ``applied_at`` and
    ``enrolled_at`` fields.
    """
    applied_at = models.DateTimeField(auto_now_add=True)
    enrolled_at = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class CIEmailField(CaseInsensitiveFieldMixin, models.EmailField):
    """
    Create an email field with case-insensitivity.
    """
    pass


class User(AbstractUser):
    username = None
    email = CIEmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    phone_number = PhoneNumberField()
    has_viewed_dashboard = models.BooleanField(default=False)
    is_archived = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the user is marked as 'archived'."
        ),
    )
    is_updated = models.BooleanField(default=False)
    last_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "The latest time the user completed an application/renewal."
        ),
    )
    last_renewal_action = models.JSONField(null=True, blank=True)
    last_action_notification_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Last user action notification",
        help_text=_(
            "The latest time a notification was sent because of or requesting user action."
        ),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email

    # Define non-database attributes
    @property
    @admin.display
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class UserHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='user_history',
        # don't remove the user history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


class AddressRD(GenericTimeStampedModel):
    address1 = models.CharField(
        max_length=200,
        default="",
        verbose_name="street address",
        help_text=_(
            "House number and street name."
        ),
    )
    address2 = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="apt, suite, etc.",
        help_text=_(
            "Leave blank if not applicable."
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
            "This can be altered by administrators if the address is outside the GMA."
        ),
    )
    has_connexion = models.BooleanField(null=True, default=None)
    is_verified = models.BooleanField(default=False)
    address_sha1 = models.CharField(max_length=40, unique=True)

    class Meta:
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    def clean(self):
        self.address1 = self.address1.upper()
        self.address2 = self.address2.upper()
        self.city = self.city.upper()
        self.state = self.state.upper()

        # Hash the address with SHA-1 (to guarantee uniqueness)
        keyList = ['address1', 'address2', 'city', 'state', 'zip_code']
        self.address_sha1 = self.hash_address(
            {key: getattr(self, key) for key in keyList}
        )

        return (self)

    @staticmethod
    def hash_address(address_dict: dict) -> str:
        """ 
        Create a SHA-1 hash from existing address values.
        :param address_dict: Dictionary of user-entered address fields.
        :returns str: String representation of SHA-1 address hash. SHA-1 hash is
            160 bits; written as hex for 40 characters.
        """
        # Explicitly define address field order
        keyList = ['address1', 'address2', 'city', 'state', 'zip_code']
        # Concatenate string representations of each value in sequence.
        # If value is string, convert to uppercase; if key DNE, use blank string.
        concatVals = ''.join(
            [address_dict[key].upper() if key in address_dict.keys() and isinstance(address_dict[key], str)
             else str(address_dict[key]) if key in address_dict.keys()
                else '' for key in keyList]
        )
        # Return SHA-1 hash of the concatenated strings
        return hashlib.sha1(bytearray(concatVals, 'utf8')).hexdigest()


# Addresses model attached to user (will delete as user account is deleted too)
class Address(GenericTimeStampedModel):
    # Default relation is the User primary key
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,   # set this to the primary key of this model
    )
    mailing_address = models.ForeignKey(
        AddressRD,
        on_delete=models.DO_NOTHING,    # don't remove this value if address is deleted
        related_name='+',   # don't relate AddressRD with this field
    )
    eligibility_address = models.ForeignKey(
        AddressRD,
        on_delete=models.DO_NOTHING,    # don't remove this value if address is deleted
        related_name='eligibility_user',
    )

    # Important: for this model, ``is_updated`` applies *only to the mailing address*
    is_updated = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    # Define non-database attributes
    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class AddressHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='address_history',
        # don't remove the address history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


# Eligibility model class attached to user (will delete as user account is deleted too)
class Household(GenericTimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,   # set this to the primary key of this model
    )
    is_updated = models.BooleanField(default=False)
    is_income_verified = models.BooleanField(
        default=False,
        verbose_name="income has been verified",
        help_text=_(
            "Designates whether an applicant has had their income verified."
        ),
    )
    duration_at_address = models.CharField(
        max_length=200,
        choices=duration_at_address_choices,
    )
    number_persons_in_household = models.IntegerField(
        default=1,
        verbose_name="household size",
        help_text=_(
            "Number of persons in the household."
        ),
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
            "Designates whether the applicant rents or owns their primary residence."
        ),
    )

    class Meta:
        verbose_name = 'household'
        verbose_name_plural = 'household'

    # Define non-database attributes
    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class HouseholdHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='household_history',
        # don't remove the household history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


class HouseholdMembers(GenericTimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,   # set this to the primary key of this model
    )

    # Store the household info (individuals' names, birthdates, and path to an uploaded ID) as JSON for
    # quick storage and reference
    household_info = models.JSONField(null=True, blank=True)
    is_updated = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'household member'
        verbose_name_plural = 'household members'

    # Define non-database attributes
    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class HouseholdMembersHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='householdmembers_history',
        # don't remove the household member history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


class IQProgramRD(GenericTimeStampedModel):
    # ``id`` is the implicity primary key
    program_name = models.CharField(
        max_length=40,
        unique=True,
        help_text=_(
            "Program reference name within the platform. "
            "Must be lowercase with no spaces."
        ),
    )

    # Store the AMI for which users must be below in order to be eligible
    ami_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text=_(
            "Income threshold of the program, as a fraction of AMI "
            "(e.g. '0.30' == 30% of AMI)."
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
            "This will be visible to users on the platform."
        ),
    )
    # Program category (as defined by the Program Lead)
    friendly_category = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly category this program is in. "
            "This will be visible to users on the platform."
        ),
    )
    # Description of the program
    friendly_description = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly description of the program. "
            "This will be visible to users on the platform."
        ),
    )
    # Supplmental information about the program (recommend leaving blank
    # (``''``) unless further info is necessary)
    friendly_supplemental_info = models.CharField(
        max_length=5000,
        help_text=_(
            "Any supplmental information to display to the user."
        ),
    )
    # Hyperlink to learn more about the program
    learn_more_link = models.CharField(
        max_length=5000,
        help_text=_(
            "Link for the user to learn more about the program."
        ),
    )
    # Estimated time period for the eligibility review (in readable text, e.g.
    # 'Two Weeks'). This should be manually updated periodically based on
    # program metrics.
    friendly_eligibility_review_period = models.CharField(
        max_length=5000,
        help_text=_(
            "The estimated time it will take to review a user's application. "
            "This will be visible to users on the platform."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Designates whether the program is in-use or not. "
            "Unselect this instead of deleting programs."
        ),
    )

    # Enable auto-apply for the designated program
    enable_autoapply = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the program should automatically apply new users who are eligible."
        ),
    )

    # All fields beginning with `requires_` are Boolean and specify whether the
    # matching field in AddressRD is a filter for the program. See
    # backend.get_eligible_iq_programs() for more detail
    requires_is_in_gma = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the user's eligibility address is required to be in the GMA to be eligible."
        ),
    )
    requires_is_city_covered = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the user's eligibility address is required to be 'covered by the City' to be eligible. "
            "'City coverage' is always True for addresses within the GMA, otherwise it's determined by the Get FoCo administrators."
        ),
    )
    # The frequency at which an IQ program needs to be renewed. If null, the
    # IQ program is considered to be a lifetime enrollment. Measured in years
    renewal_interval_year = models.IntegerField(
        null=True,
        verbose_name="renewal interval in years",
        help_text=_(
            "The frequency at which a user needs to renew their application for this IQ program. "
            "Leave blank for a non-renewing (lifetime-enrollment) program."
        ),
    )

    class Meta:
        verbose_name = 'IQ program'
        verbose_name_plural = 'IQ programs'

    def __str__(self):
        return str(self.friendly_name)


class IQProgram(IQProgramTimeStampedModel):
    """ Model class to store each user's program enrollment status.

    Note that the record for a program is created when a user applies (at which
    point ``applied_at`` is timestamped) and ``is_enrolled`` is set to ``True``
    and ``enrolled_at`` is timestamped when income verification is complete.

    """

    # ``id`` is the implicit primary key
    user = models.ForeignKey(
        User,
        related_name='iq_programs',
        on_delete=models.CASCADE,
    )

    program = models.ForeignKey(
        IQProgramRD,
        related_name='iq_programs',
        on_delete=models.DO_NOTHING,    # don't update these values if the program is deleted
    )

    is_enrolled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "user IQ program"
        verbose_name_plural = "user IQ programs"

    # Define non-database attributes
    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class IQProgramHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='iqprogram_history',
        # don't remove the iq program history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


class EligibilityProgramRD(GenericTimeStampedModel):
    """
    Model class to store the eligibility programs.
    """
    # ``id`` is the implicit primary key
    program_name = models.CharField(
        max_length=40,
        unique=True,
        help_text=_(
            "Program reference name within the platform. "
            "Must be lowercase with no spaces."
        ),
    )

    # Store the AMI threshold that the users with each program are underneath
    ami_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text=_(
            "Income threshold of the program, as a fraction of AMI "
            "(e.g. '0.30' == 30% of AMI)"
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
            "This will be visible to users on the platform."
        ),
    )
    friendly_description = models.CharField(
        max_length=5000,
        help_text=_(
            "The user-friendly description of the program. "
            "This will be visible to users on the platform."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Designates whether the program is in-use or not. "
            "Unselect this instead of deleting programs."
        ),
    )

    class Meta:
        verbose_name = 'eligibility program'
        verbose_name_plural = 'eligibility programs'

    def __str__(self):
        return str(self.friendly_name)


class EligibilityProgram(GenericTimeStampedModel):
    """
    Model class to store the eligibility programs.
    """
    # ``id`` is the implicit primary key
    user = models.ForeignKey(
        User,
        related_name='eligibility_files',
        on_delete=models.CASCADE,
    )

    program = models.ForeignKey(
        EligibilityProgramRD,
        on_delete=models.DO_NOTHING,  # don't remove the program ID if the program is deleted
    )

    # Upload the file(?) to the proper directory in Azure Blob Storage and store
    # the path
    document_path = models.FileField(
        max_length=5000, upload_to=userfiles_path, null=True, default=None)
    
    class Meta:
        verbose_name = "user eligibility program"
        verbose_name_plural = "user eligibility programs"

    # Define non-database attributes
    @property
    def update_mode(self):
        # Return update_mode for use in saving historical values
        return getattr(self, '_update_mode', False)

    @update_mode.setter
    def update_mode(self, val):
        # Setter for update_mode
        self._update_mode = val

    @property
    def renewal_mode(self):
        # Return renewal_mode for use in saving historical values
        return getattr(self, '_renewal_mode', False)

    @renewal_mode.setter
    def renewal_mode(self, val):
        # Setter for renewal_mode
        self._renewal_mode = val


class EligibilityProgramHist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        related_name='eligibility_program_history',
        # don't remove the eligibility program history if a user account is deleted
        on_delete=models.DO_NOTHING,
    )
    created = models.DateTimeField(auto_now_add=True)
    historical_values = models.JSONField(null=True, blank=True)


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user_id.id, filename)


class Feedback(TimeStampedModel):
    star_rating = models.CharField(
        max_length=1
    )
    feedback_comments = models.TextField(
        max_length=500
    )

    class Meta:
        verbose_name = verbose_name_plural = 'feedback'

class Admin(models.Model):
    """ A model for admin-related user data. """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin',
        primary_key=True,   # set this to the primary key of this model
    )

    awaiting_user_response = models.BooleanField(
        default=False,
        help_text=_(
            "Designates that the admin is waiting for a user to respond to a request made separate from this platform. "
            "This is used only to filter income-verification applicants."
        ),
    )

    internal_notes = models.TextField(
        blank=True,
        help_text=_(
            "Notes pertaining to this user, for internal use. "
            "This field is not visible to applicants."
        ),
    )

    class Meta:
        verbose_name = verbose_name_plural = 'administration'
