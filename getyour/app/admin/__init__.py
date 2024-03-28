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
import logging
from decimal import Decimal
from django.http import HttpRequest
import pendulum

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ngettext
from django.conf import settings
from django.db.models import F
from django.shortcuts import reverse
from django.db.models.functions import Lower

from app.models import (
    User,
    Address,
    AddressRD,
    Household,
    HouseholdMembers,
    EligibilityProgram,
    IQProgram,
)
from app.forms import UserUpdateForm


def create_modeladmin(
        modeladmin,
        model,
        name=None,
        pretty_name=None,
    ):
    """
    Create a proxy ModelAdmin to allow different views for different users on
    the same model.
    
    """
    
    class Meta:
        proxy = True
        app_label = model._meta.app_label
        verbose_name = pretty_name

    attrs = {'__module__': '', 'Meta': Meta}

    newmodel = type(name, (model,), attrs)

    admin.site.register(newmodel, modeladmin)
    return modeladmin


class AddressInline(admin.TabularInline):
    model = Address
    
    fk_name = "user"

    readonly_fields = ('created_at', 'modified_at', 'mailing_addr', 'eligibility_addr')
    fieldsets = [
        (
            None,
            {
                'fields': ('created_at', 'modified_at', 'mailing_addr', 'eligibility_addr'),
            },
        ),
    ]

    @admin.display(description='mailing address')
    def mailing_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.mailing_address_id)
        if addr.address2 == '':
            return f"{addr.address1}\n{addr.city}, {addr.state} {addr.zip_code}"
        else:
            return f"{addr.address1}\n{addr.address2}\n{addr.city}, {addr.state} {addr.zip_code}"

    @admin.display(description='eligibility address')
    def eligibility_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.eligibility_address_id)
        if addr.address2 == '':
            return f"{addr.address1}\n{addr.city}, {addr.state} {addr.zip_code}"
        else:
            return f"{addr.address1}\n{addr.address2}\n{addr.city}, {addr.state} {addr.zip_code}"

    # Show zero extra (unfilled) options
    extra = 0


class HouseholdInline(admin.TabularInline):
    model = Household
    
    fk_name = "user"

    readonly_fields = ('created_at', 'modified_at', 'duration_at_address', 'rent_or_own', 'income_percent')
    fieldsets = [
        (
            None,
            {
                'fields': ('created_at', 'modified_at', 'duration_at_address', 'rent_or_own', 'income_percent'),
            },
        ),
    ]

    @admin.display(description='rent or own')
    def rent_or_own(self, obj):
        return obj.rent_own.capitalize()

    @admin.display(description='income relative to AMI')
    def income_percent(self, obj):
        # As some point when the stack is called, income_as_fraction_of_ami may
        # return None; the 'or' ensures this won't error out
        return "{:.0f}%".format(100*(obj.income_as_fraction_of_ami or 0))

    # Show zero extra (unfilled) options
    extra = 0


class HouseholdMembersInline(admin.TabularInline):
    model = HouseholdMembers

    fk_name = "user"

    readonly_fields = ('created_at', 'modified_at', 'household_info_parsed')
    fieldsets = [
        (
            None,
            {
                'fields': ('created_at', 'modified_at', 'household_info_parsed'),
            },
        ),
    ]

    @admin.display(description='individuals in household')
    def household_info_parsed(self, obj):
        person_list = []
        if obj.household_info is not None:
            for itm in obj.household_info['persons_in_household']:
                # Add information, then path to identification file and a blank line
                person_list.append(f"{itm['name']} (DOB: {itm['birthdate']})")

                # Parse each document_path into a link that can be used to view the
                # file
                person_list.append(
                    """<a href="{trg}" onclick="javascript:window.open(this.href, 'newwindow', 'width=600, height=600'); return false;">View Identification</a>""".format(
                        trg=reverse(
                            'app:admin_view_file',
                            kwargs={'blob_name': itm['identification_path']},
                        ),
                    )
                )
                person_list.append('')

        return format_html('<br />'.join(person_list))

    # Show zero extra (unfilled) options
    extra = 0


class EligibilityProgramInline(admin.TabularInline):
    def get_queryset(self, request):
        """ Override ordering to use program friendly name instead. """
        qs = super(EligibilityProgramInline, self).get_queryset(request)
        qs = qs.order_by('program__friendly_name')
        return qs

    model = EligibilityProgram

    fk_name = "user"

    readonly_fields = ('created_at', 'modified_at', 'program_name', 'document_path_parsed')
    fieldsets = [
        (
            None,
            {
                'fields': ('created_at', 'modified_at', 'program_name', 'document_path_parsed'),
            },
        ),
    ]

    @admin.display(description='program')
    def program_name(self, obj):
        return obj.program.friendly_name

    @admin.display(description='document')
    def document_path_parsed(self, obj):
        """
        Parse each document_path into a link that can be used to view the
        files.

        This function spoofs the URLs that ``django-storages`` creates
        automatically; this could be eliminated (except for the headers) if the
        data model was updated to save one file per record.
        
        """

        # Parse the stringified list of document_path values. Dynamically
        # converting to a list would be dangerous, so this is processed manually.
        blob_list = obj.document_path.name.replace(
            "['", ''
        ).replace(
            "']", ''
        ).split(
            ', '
        )
        url_list = []
        for idx, itm in enumerate(blob_list):
            url_list.append(
                """<a href="{trg}" onclick="javascript:window.open(this.href, 'newwindow', 'width=600, height=600'); return false;">View Document {nm} of {tot}</a>""".format(
                    trg=reverse(
                        'app:admin_view_file',
                        kwargs={'blob_name': itm},
                    ),
                    nm=idx+1,
                    tot=len(blob_list),
                )
            )

        # return format_html(url_list[0])
        return format_html('<br />'.join(url_list))

    # Show zero extra (unfilled) options
    extra = 0


class IQProgramInline(admin.TabularInline):
    def get_queryset(self, request):
        """ Override ordering to use program friendly name instead. """
        qs = super(IQProgramInline, self).get_queryset(request)
        qs = qs.order_by('program__friendly_name')
        return qs

    model = IQProgram

    fk_name = "user"

    readonly_fields = ('program_name', 'applied_at', 'enrollment_status')
    fieldsets = [
        (
            None,
            {
                'fields': ('program_name', 'applied_at', 'enrollment_status'),
            },
        ),
    ]

    @admin.display(description='program')
    def program_name(self, obj):
        return obj.program.friendly_name

    @admin.display(description='enrolled at')
    def enrollment_status(self, obj):
        if obj.is_enrolled:
            ts = pendulum.obj(obj.enrolled_at)
            ts_formatted = "{} {}.".format(
                ts.format('MMM D, YYYY, h:mm'),
                # Manually format the am/pm designator to match the Django ones
                '.'.join(ts.format('A').lower()),
            )
            return ts_formatted
        else:
            return "Not enrolled"

    # Show zero extra (unfilled) options
    extra = 0


class UserAdmin(admin.ModelAdmin):
    search_fields = ('last_name__startswith', 'first_name__startswith', 'email')
    list_display = ('last_name', 'first_name', 'email', 'last_completed_at')
    ordering = (Lower('last_name'), Lower('first_name'))    # case-insensitive
    list_display_links = ('email', )
    date_hierarchy = 'last_completed_at'

    # Calculated fields must be defined as read-only
    readonly_fields = ('full_name',)
    fieldsets = [
        (
            'USER',
            {
                'fields': (
                    'full_name',
                    'email',
                    'phone_number',
                ),
            },
        ),
        (
            'APPLICATION',
            {
                'fields': (
                    'date_joined',
                    'last_login',
                    'last_completed_at',
                    'has_viewed_dashboard',
                    # 'last_application_action',
                    'last_renewal_action',
                ),
            },
        ),
    ]

    inlines = [
        AddressInline,
        HouseholdInline,
        HouseholdMembersInline,
        EligibilityProgramInline,
        IQProgramInline,
    ]

    list_per_page = 100


admin.site.register(User, UserAdmin)
