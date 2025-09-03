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

from django.contrib import admin
from django.db.models import Exists, OuterRef
from django.utils.translation import gettext_lazy as _

from app.models import EligibilityProgram, User


def needs_income_verification_filter(queryset):
    """
    Filter a queryset for users that need income verification.

    """

    # Gather EligibilityProgram objects for each user that are 'active'
    selected_active_programs = EligibilityProgram.objects.filter(
        user_id=OuterRef("id"),
        program__is_active=True,
    )

    # Gather EligibilityProgram objects for each user that are 'active' and have
    # an uploaded file
    active_incomplete_programs = EligibilityProgram.objects.filter(
        user_id=OuterRef("id"),
        program__is_active=True,
        document_path="",
    )

    queryset = queryset.filter(
        # User has at least one active eligibility program
        Exists(selected_active_programs),
        # User doesn't have any incomplete eligibility programs (e.g. file not
        # uploaded)
        ~Exists(active_incomplete_programs),
        # When enabled, this will (should) supersede the previous Exists() cases:
        # (even though it won't guarantee an *active* eligibility program, any users still need to show up in this filter)
        # # Ensure the user isn't in the middle of the initial application
        # last_application_action__isnull=True,
        # Ensure the user isn't in the middle of a renewal
        last_renewal_action__isnull=True,
        # User has completed the application (non-null last_completed_at)
        last_completed_at__isnull=False,
        # User is not 'archived'
        is_archived=False,
        # User's household is not 'income verified'
        household__is_income_verified=False,
    )

    # Ensure all identification is included
    filter_ids = []
    for usr in queryset:
        if "persons_in_household" in usr.householdmembers.household_info and all(
            "identification_path" in x and x["identification_path"] is not None
            for x in usr.householdmembers.household_info["persons_in_household"]
        ):
            filter_ids.append(usr.id)

    # Recreate queryset with filter_ids and return
    return User.objects.filter(id__in=filter_ids)


class NeedsVerificationListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _("income verification")

    # Parameter for the filter that will be used in the URL query
    parameter_name = "needsverification"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ("new", _("New Needs Verification")),
            ("hold", _("Awaiting Response")),
            ("all", _("All Needs Verification")),
            ("done", _("Has Been Verified")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == "new":
            return needs_income_verification_filter(queryset).exclude(
                admin__awaiting_user_response=True,
            )
        if self.value() == "hold":
            return needs_income_verification_filter(queryset).filter(
                admin__awaiting_user_response=True,
            )
        if self.value() == "all":
            return needs_income_verification_filter(queryset)
        if self.value() == "done":
            return queryset.filter(
                household__is_income_verified=True,
            )


class GMAListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _("GMA")

    # Parameter for the filter that will be used in the URL query
    parameter_name = "gma"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ("in", _("Within GMA")),
            ("out", _("Outside of GMA")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == "in":
            return queryset.filter(
                is_in_gma=True,
            )
        if self.value() == "out":
            return queryset.filter(
                is_in_gma=False,
            )


class CityCoveredListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _("City coverage")

    # Parameter for the filter that will be used in the URL query
    parameter_name = "citycovered"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ("yes", _("City covered")),
            ("no", _("not City covered")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == "yes":
            return queryset.filter(
                is_city_covered=True,
            )
        if self.value() == "no":
            return queryset.filter(
                is_city_covered=False,
            )


class AccountDisabledListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _("account disabled")

    # Parameter for the filter that will be used in the URL query
    parameter_name = "disabled"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            (None, _("Not disabled")),
            ("true", _("Disabled")),
            ("all", _("All")),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": cl.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() is None:
            return queryset.filter(
                is_archived=False,
            )
        if self.value() == "true":
            return queryset.filter(
                is_archived=True,
            )
        if self.value() == "all":
            return queryset


class NeedsEnrollmentListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _("enrollment")

    # Parameter for the filter that will be used in the URL query
    parameter_name = "needsenrollment"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ("yes", _("Needs Enrollment")),
            ("no", _("Has Been Enrolled")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == "yes":
            return queryset
        if self.value() == "no":
            return queryset
