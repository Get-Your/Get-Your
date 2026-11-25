"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2026

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
from django.db.models import Exists, OuterRef, Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _

from app.models import EligibilityProgram, IQProgram, User


def complete_and_unverified_filter(
    queryset: QuerySet,
) -> QuerySet:
    """
    Filter a queryset for users that have completed their application/renewal.

    Parameters
    ----------
    queryset : QuerySet
        The QuerySet passed to the filter. Since this is for the User
        changelist, this will be a QuerySet of users.

    Returns
    -------
    QuerySet
        Returns the filtered QuerySet.

    """

    # Gather active IQProgram objects for each user
    applied_programs = IQProgram.objects.filter(
        user_id=OuterRef("id"),
        program__is_active=True,
    )

    # Filter the queryset. Note that keyword filters are wrapped in Q() so that
    # the filter order can be optimized
    queryset = queryset.filter(
        # User is not 'archived'
        Q(is_archived=False),
        # User has completed the application (non-null last_completed_at)
        Q(last_completed_at__isnull=False),
        # User is not in the middle of a renewal
        Q(last_renewal_action__isnull=True),
        # User's household is not 'income verified'
        Q(household__is_income_verified=False),
        # User has applied for at least one program (as a proxy for the account
        # being eligible)
        Exists(applied_programs),
    )

    return queryset


def complete_except_documentation_filter(
    queryset: QuerySet,
) -> QuerySet:
    """
    Filter a queryset for users that have completed their application but are
    missing documentation.

    Parameters
    ----------
    queryset : QuerySet
        The QuerySet passed to the filter. Since this is for the User
        changelist, this will be a QuerySet of users.

    Returns
    -------
    QuerySet
        Returns the filtered QuerySet.

    """

    # Gather active EligibilityProgram objects for each user that have an
    # empty file upload
    incomplete_eligibility_programs = EligibilityProgram.objects.filter(
        Q(user_id=OuterRef("id")),
        Q(program__is_active=True),
        Q(Q(document_path="") | Q(document_path="[]")),
    )

    # Gather users with a complete application and exclude those that have
    # EligibilityProgram objects with empty documents
    queryset = complete_and_unverified_filter(queryset)

    # Remove all users from `queryset` that have all their EligibilityProgram
    # documents
    missing_eligibility_qs = queryset.filter(
        Exists(incomplete_eligibility_programs)
    )

    # Include only users that are missing any identification documentation (of
    # the subset of users that are ready for income verification).
    # This loops through `queryset` so that the JSON in User.householdmembers
    # can be parsed for each usery
    filter_ids = []
    for usr in queryset:
        if (
            "persons_in_household" not in usr.householdmembers.household_info or (
                "persons_in_household" in usr.householdmembers.household_info and any(
                    "identification_path" in x and x["identification_path"] is None
                    for x in usr.householdmembers.household_info["persons_in_household"]
                )
            )
        ):
            filter_ids.append(usr.id)

    # Recreate queryset with filter_ids
    missing_identification_qs = User.objects.filter(id__in=filter_ids)

    # Return the joined QuerySet, with distinct values
    return (missing_eligibility_qs | missing_identification_qs).distinct()


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
            ("docs", _("New Needs Documentation")),
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
            return complete_and_unverified_filter(
                queryset
            ).filter(
                admin__awaiting_user_response=False,
            )

        if self.value() == "docs":
            return complete_except_documentation_filter(
                queryset,
            ).filter(
                admin__awaiting_user_response=False,
            )

        if self.value() == "hold":
            return complete_and_unverified_filter(
                queryset
            ).filter(
                admin__awaiting_user_response=True,
            )

        if self.value() == "all":
            return complete_and_unverified_filter(queryset)

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
