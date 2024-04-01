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
from django.db.models import Exists, OuterRef
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from app.models import EligibilityProgram

class NeedsVerificationListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _('income verification')

    # Parameter for the filter that will be used in the URL query
    parameter_name = 'needsverification'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ('yes', _('Needs Verification')),
            ('no', _('Already Verified')),
            # ('all', _('all users')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == 'yes':
            # Use the logic from Get-Your-utils python.run_extracts
            return queryset.filter(
                # User has at least one eligibility program that is 'active'
                Exists(
                    EligibilityProgram.objects.filter(
                        user=OuterRef('pk'),    # use the current outer reference
                        program__is_active=True,
                    )
                ),
                # User has no programs with missing files
                ~Exists(
                    EligibilityProgram.objects.filter(
                        user=OuterRef('pk'),    # use the current outer reference
                        document_path__exact='',
                    )
                ),
                # User is not 'archived'
                is_archived=False,
                # User's household is not 'income verified'
                household__is_income_verified=False,
                # User's addresses are verified (via USPS)
                address__eligibility_address__is_verified=True,
                address__mailing_address__is_verified=True,
            )
        if self.value() == 'no':
            return queryset.filter(
                household__is_income_verified=True,
            )
    

class GMAListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _('GMA')

    # Parameter for the filter that will be used in the URL query
    parameter_name = 'gma'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.

        """
        return (
            ('in', _('Within GMA')),
            ('out', _('Outside of GMA')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == 'in':
            return queryset.filter(
                is_in_gma=True,
            )
        if self.value() == 'out':
            return queryset.filter(
                is_in_gma=False,
            )
        

class CityCoveredListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options
    title = _('City Coverage')

    # Parameter for the filter that will be used in the URL query
    parameter_name = 'citycovered'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded
        value for the option that will appear in the URL query (and therefore
        should be a string). The second element is the human-readable name for
        the option that will appear in the right sidebar.
        
        """
        return (
            ('yes', _('City covered')),
            ('no', _('not City covered')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.

        """
        # Compare the requested value to decide how to filter the queryset
        if self.value() == 'yes':
            return queryset.filter(
                is_city_covered=True,
            )
        if self.value() == 'no':
            return queryset.filter(
                is_city_covered=False,
            )
