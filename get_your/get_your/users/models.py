from typing import ClassVar

from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_case_insensitive_field import CaseInsensitiveFieldMixin
from phonenumber_field.modelfields import PhoneNumberField

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
    email = CIEmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    phone_number = PhoneNumberField()
    has_viewed_dashboard = models.BooleanField(default=False)
    last_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "The latest time the user completed an application/renewal.",
        ),
    )

    # Define user-updated data
    user_has_updated = models.BooleanField(default=False)
    user_application_status = models.JSONField(null=True, blank=True)

    # Define system-updated data
    last_action_notification_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last user action notification",
        help_text=_(
            "The latest time a notification was sent because of or requesting user action.",
        ),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

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
