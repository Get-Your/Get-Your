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

from typing import TYPE_CHECKING

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager

if TYPE_CHECKING:
    from .models import User  # noqa: F401


class UserManager(DjangoUserManager["User"]):
    """Custom manager for the User model."""

    def _ci_email_transfrom(self, kwargs):
        """Convert all lookups that include 'email' to be case-insensitive.

        'Email' must be case-insensitive-unique, but is not coerced to a
        specific case (to be in full compliance with RFC 5321, which allows
        for case-sensitive addresses
        (https://www.rfc-editor.org/rfc/rfc5321#section-2.3.11)); this
        replaces any lookups on 'email' with their corresponding
        case-insensitive version.

        """
        if "email" in kwargs:
            # When no lookup type is included, 'exact' is implied
            kwargs["email__iexact"] = kwargs.pop("email")
        if "email__contains" in kwargs:
            kwargs["email__icontains"] = kwargs.pop("email__contains")
        if "email__startswith" in kwargs:
            kwargs["email__istartswith"] = kwargs.pop("email__startswith")
        if "email__endswith" in kwargs:
            kwargs["email__iendswith"] = kwargs.pop("email__endswith")
        if "email__regex" in kwargs:
            kwargs["email__iregex"] = kwargs.pop("email__regex")

        return kwargs

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            msg = "The given email must be set"
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self._create_user(email, password, **extra_fields)

    def get(self, *args, **kwargs):
        """Updates get() to use case-insensitive email."""
        kwargs = self._ci_email_transfrom(kwargs)
        return super().get_queryset().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        """Updates filter() to use case-insensitive email."""
        kwargs = self._ci_email_transfrom(kwargs)
        return super().get_queryset().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        """Updates exclude() to use case-insensitive email."""
        kwargs = self._ci_email_transfrom(kwargs)
        return super().get_queryset().exclude(*args, **kwargs)
