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

import logging
from itertools import chain

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import LogEntry
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms.widgets import Textarea
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from app.admin.filters import CityCoveredListFilter
from app.admin.filters import GMAListFilter
from app.admin.forms import EligibilityProgramRefForm
from app.admin.forms import IQProgramRefForm
from app.admin.models import StaffPermissions
from app.backend import finalize_application
from app.backend import remove_ineligible_programs_for_user
from app.backend import update_users_for_program
from app.backend.address import address_check
from app.backend.address import finalize_address
from app.models import Address
from app.models import IQProgram
from dashboard.backend import get_iqprogram_requires_fields
from monitor.wrappers import LoggerWrapper

from .models import Address as AddressRef
from .models import EligibilityProgram as EligibilityProgramRef
from .models import IQProgram as IQProgramRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


# Get the user model
User = get_user_model()


@admin.register(AddressRef)
class AddressRefAdmin(admin.ModelAdmin):
    search_fields = ("address1", "address2")
    list_display = ("address1", "address2", "is_in_gma", "is_city_covered")
    ordering = list_display_links = ("address1", "address2")
    list_filter = (GMAListFilter, CityCoveredListFilter)
    actions = ["update_gma"]

    all_possible_change_fields = [
        "pretty_address",
        "is_in_gma",
        "is_city_covered",
    ]

    @admin.display(description="address")
    def pretty_address(self, obj):
        if obj.address2 == "":
            return f"{obj.address1}\n{obj.city}, {obj.state} {obj.zip_code}"
        return f"{obj.address1}\n{obj.address2}\n{obj.city}, {obj.state} {obj.zip_code}"

    list_per_page = 100

    def get_changelist(self, request, **kwargs):
        # Log entrance to this changelist. This attempts to track called
        # functions
        log.debug(
            "Entering admin changelist",
            function="AddressRefAdmin",
            user_id=request.user.id,
        )

        return super().get_changelist(request, **kwargs)

    def get_fields(self, request, obj=None):
        """
        Return fields based on whether object exists (new or existing).

        Existing addresses can only update is_city_covered, when applicable.
        New addresses can only enter the address information itself.

        """

        # Log entrance to this change page. This attempts to track called
        # functions
        log.debug(
            "Entering admin change page",
            function="AddressRefAdmin",
            user_id=request.user.id,
        )

        # Parse the available permissions and those of the request user. This is
        # defined here because it runs before get_readonly_fields()
        request.user.staff_permissions = StaffPermissions(request.user)

        if obj is None:
            fields = [
                "address1",
                "address2",
                ("city", "state"),
                "zip_code",
            ]
        else:
            fields = self.all_possible_change_fields

        return fields

    def get_readonly_fields(self, request, obj=None):
        """
        Return readonly fields based on GMA status.

        """
        # Use the `_available_groups` attribute so the Enum groups are
        # comparable (they must originate in the same module)
        permission_groups = request.user.staff_permissions._available_groups

        # If obj is None (as in, adding a new address), there are no readonly
        # fields
        if obj is None:
            return []

        # Global readonly fields
        readonly_fields = self.all_possible_change_fields

        readonly_remove = []
        # is_city_covered can be modified only if is_in_gma==False and user is
        # either superuser or in 'admin' group
        if not obj.is_in_gma and (
            request.user.staff_permissions.contains(
                permission_groups.SUPERUSER,
                permission_groups.PROGRAM_ADMIN,
            )
        ):
            readonly_remove.append("is_city_covered")

        # Remove the fields and re-listify
        return list(set(readonly_fields) - set(readonly_remove))

    @admin.action(description="Update GMA for selected addresses")
    def update_gma(self, request, input_object):
        """
        Update the GMA of the selected object(s).

        This is used both as a changelist action and a page-specific button, so
        ``input_object`` can be either a single object (of the modeladmin type)
        or a queryset from the changelist actions.

        """

        # Log entrance to this action. This attempts to track called
        # functions
        log.debug(
            "Entering admin action",
            function="update_gma",
            user_id=request.user.id,
        )

        # If the input_object is not a QuerySet, coerce it into a list so for
        # similar operation
        if isinstance(input_object, QuerySet):
            queryset = input_object
        else:
            queryset = [input_object]

        # Loop through the queryset (or simulated queryset)
        updated_addr_count = 0
        for obj in queryset:
            # Format for address_check. All addresses in the database have been
            # through USPS, so no need to re-validate (just copy formatting)
            address_dict = {
                "AddressValidateResponse": {
                    "Address": {
                        # Note 1 & 2 are swapped
                        "Address1": obj.address2,
                        "Address2": obj.address1,
                        "City": obj.city,
                        "State": obj.state,
                        "Zip5": obj.zip_code,
                    },
                },
            }

            # Run the address check and make the final adjustments
            (is_in_gma, has_connexion) = address_check(address_dict)

            # Only make changes if there is an update
            if is_in_gma != obj.is_in_gma:
                updated_addr_count += 1
                finalize_address(obj, is_in_gma, has_connexion)

                # Add a log entry to admin that the address was updated
                _ = LogEntry.objects.log_action(
                    user_id=request.user.id,
                    # Use the target object from here
                    content_type_id=ContentType.objects.get_for_model(obj).pk,
                    object_id=obj.id,
                    object_repr=str(obj),
                    action_flag=CHANGE,
                    change_message="Changed Is in GMA.",
                )

                # Loop through any users with this as their eligibility address
                # and correct their application if they have already completed it
                for addr in obj.eligibility_user.all():
                    if addr.user.last_completed_at is not None:
                        _ = finalize_application(addr.user, update_user=False)

                        # Remove any no-longer-eligible programs
                        remove_ineligible_programs_for_user(
                            addr.user.id,
                            admin_mode=True,
                        )

        log.info(
            f"{len(queryset)} addresses checked; updates applied to {updated_addr_count}.",
            function="update_gma",
            user_id=request.user.id,
        )

        # Add a message to the user when complete
        self.message_user(
            request,
            ngettext(
                "GMA update was executed for %d address.",
                "GMA update was executed for %d addresses.",
                len(queryset),
            )
            % len(queryset),
            messages.SUCCESS,
        )

    # Temporarily redirect the user to an error message if trying to add new
    def add_view(self, request, form_url="", extra_context=None):
        # Parse the available permissions and those of the request user; this
        # is defined here as the first request-based function to be called for
        # an 'add' page
        request.user.staff_permissions = StaffPermissions(request.user)

        self.message_user(
            request,
            "Sorry, that isn't available yet.",
            messages.ERROR,
        )

        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        redirect_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_changelist",
            current_app=self.admin_site.name,
        )
        redirect_url = add_preserved_filters(
            {
                "preserved_filters": preserved_filters,
                "opts": opts,
            },
            redirect_url,
        )
        return HttpResponseRedirect(redirect_url)

    # Add custom buttons to the save list in the admin template (from
    # https://stackoverflow.com/a/34899874/5438550 and
    # https://stackoverflow.com/a/69487616/5438550)
    change_form_template = "admin/custom_button_change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # Parse the available permissions and those of the request user; this
        # is defined here as the first request-based function to be called for a
        # change page
        request.user.staff_permissions = StaffPermissions(request.user)

        # Add any custom buttons. This must be a list/tuple of list/tuples, as
        # (name, url). The 'url' portion must match the
        # "if 'url' in request.POST:" section of response_change()
        extra_context["custom_buttons"] = [
            {
                # Buttons that open in the same window save the model first
                "title": "Save and update GMA",
                "link": "_update_gma",
            },
        ]
        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def response_change(self, request, obj):
        opts = self.model._meta
        pk_value = obj._get_pk_val()
        preserved_filters = self.get_preserved_filters(request)

        if "_update_gma" in request.POST:
            # Handle 'Update GMA': run the logic to update ``is_in_gma`` then
            # refresh the page
            self.update_gma(request, obj)

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    "preserved_filters": preserved_filters,
                    "opts": opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        # Set admin_mode for proper signals functionality
        obj.admin_mode = True

        super().save_model(request, obj, form, change)


@admin.register(EligibilityProgramRef)
class EligibilityProgramRefAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Override ordering to use friendly name instead."""
        qs = super().get_queryset(request)
        qs = qs.order_by("friendly_name")
        return qs

    search_fields = ("friendly_name",)
    list_display = ("friendly_name", "is_active", "ami_threshold")
    list_filter = ("is_active",)
    list_display_links = ("friendly_name",)

    def get_changelist(self, request, **kwargs):
        # Log entrance to this changelist. This attempts to track called
        # functions
        log.debug(
            "Entering admin changelist",
            function="EligibilityProgramRefAdmin",
            user_id=request.user.id,
        )

        return super().get_changelist(request, **kwargs)

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Log entrance to this change page. This attempts to track called
        # functions
        log.debug(
            "Entering admin change page",
            function="EligibilityProgramRefAdmin",
            user_id=request.user.id,
        )

        kwargs["form"] = EligibilityProgramRefForm
        return super().get_form(request, obj=obj, change=change, **kwargs)

    list_per_page = 100


@admin.register(IQProgramRef)
class IQProgramRefAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Override ordering to use friendly name instead."""
        qs = super().get_queryset(request)
        qs = qs.order_by("friendly_name")
        return qs

    search_fields = ("friendly_name",)
    list_display = ("friendly_name", "is_active")
    list_filter = ("is_active",)
    list_display_links = ("friendly_name",)

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs["form"] = IQProgramRefForm
        return super().get_form(request, obj=obj, change=change, **kwargs)

    list_per_page = 100

    # Perform additional logic if any of the 'requires' fields are altered; save
    # the model or perform a dry run based on the input to this function
    def get_changes(self, request, obj, form, change, view_only=True):
        # If this is an addition (not change) or the changed_data is empty (not
        # form.changed_data), add a message and go directly to display
        if not change or not form.changed_data:
            affected_users = {
                "permissive": [],
                "restrictive": [],
            }
            log.info(
                f"No changes detected (view_only=={view_only})",
                function="IQProgramRefAdmin.get_changes",
                user_id=request.user.id,
            )

            if view_only:
                user_message = (
                    "There are no tests for the specified action; proceed at will."
                )
            else:
                user_message = "No changes detected."
            self.message_user(
                request,
                user_message,
                messages.SUCCESS,
            )

        else:
            req_fields = get_iqprogram_requires_fields()

            # For each itm that is a 'requires' field, calculate how many
            # active accounts may be affected and alert the user

            # Gather all 'requires' fields that were updated vs not
            updated_fields = [x for x in req_fields if x[0] in form.changed_data]

            # If none of the updated fields are in req_fields, go directly to
            # display
            if len(updated_fields) == 0:
                affected_users = {
                    "permissive": [],
                    "restrictive": [],
                }
                log.debug(
                    f"'Requires' field update not detected (view_only=={view_only})",
                    function="IQProgramRefAdmin.get_changes",
                    user_id=request.user.id,
                )

            else:
                log.info(
                    "'Requires' field update detected ({}) (view_only=={})".format(
                        ", ".join([x[0] for x in updated_fields]),
                        view_only,
                    ),
                    function="IQProgramRefAdmin.get_changes",
                    user_id=request.user.id,
                )

                # Determine affected users based on currently eligibility vs
                # proposed eligibility for the changes

                # Build Q queries to filter addresses that are ineligible (both
                # currently and after the proposed changes)
                filter_criteria = {
                    f"eligibility_address__{cor}": False
                    for req, cor in req_fields
                    if form.initial[req] is True
                }
                # Use OR to match *any of* the fields
                filter_currently_ineligible = Q(
                    **filter_criteria,
                    _connector="OR",
                )

                filter_criteria = {
                    f"eligibility_address__{cor}": False
                    for req, cor in req_fields
                    if form.cleaned_data[req] is True
                }
                # Use OR to match *any of* the fields
                filter_proposed_ineligible = Q(
                    **filter_criteria,
                    _connector="OR",
                )

                # Build Q queries to filter addresses that are eligible (both
                # currently and after the proposed changes)
                filter_criteria = {
                    f"eligibility_address__{cor}": True
                    for req, cor in req_fields
                    if form.initial[req] is True
                }
                # Use the default AND to match *all* fields
                filter_currently_eligible = Q(**filter_criteria)

                filter_criteria = {
                    f"eligibility_address__{cor}": True
                    for req, cor in req_fields
                    if form.cleaned_data[req] is True
                }
                # Use the default AND to match *all* fields
                filter_proposed_eligible = Q(**filter_criteria)

                # Gather any IQProgram objects for each user for the specified
                # program (if this DNE for a user, they haven't applied to the
                # program)
                applied_iq_objects = IQProgram.objects.filter(
                    user_id=OuterRef("id"),
                    program_id=obj.id,
                )

                # Initialize the affected users dict, using empty lists as
                # effective placeholders for querysets
                affected_users = {
                    "permissive": [],
                    "restrictive": [],
                }

                # Gather any address for each user for the 'permissive' and
                # 'restrictive' cases (an address that is currently ineligible
                # but would be eligible with the proposed changes and vice
                # versa, respectively)
                permissive_address = Address.objects.select_related(
                    "eligibility_address",
                ).filter(
                    filter_currently_ineligible,
                    filter_proposed_eligible,
                    user_id=OuterRef("id"),
                )

                restrictive_address = Address.objects.select_related(
                    "eligibility_address",
                ).filter(
                    filter_currently_eligible,
                    filter_proposed_ineligible,
                    user_id=OuterRef("id"),
                )

                # Gather all active users with complete applications that
                # include the affected addresses and have applied for the
                # specified IQ program
                affected_users["restrictive"] = User.objects.select_related(
                    "address",
                ).filter(
                    # User has an address affected by this change
                    Exists(restrictive_address),
                    # User has applied for the specified IQ program
                    Exists(applied_iq_objects),
                    is_archived=False,
                    last_completed_at__isnull=False,
                )

                affected_users["permissive"] = User.objects.select_related(
                    "address",
                ).filter(
                    # User has an address affected by this change
                    Exists(permissive_address),
                    # User cannot have applied to the specific IQ program, since
                    # they are currently ineligible
                    is_archived=False,
                    last_completed_at__isnull=False,
                )

                # Update affected users after the model was saved (if applicable)
                if not view_only:
                    # Update each user for the specified program and collect the
                    # counts of changes
                    users = list(
                        chain(
                            affected_users["permissive"],
                            affected_users["restrictive"],
                        ),
                    )

                    affected_counts = update_users_for_program(
                        program=obj,
                        users=users,
                    )

                    user_message = "Users affected by the change to “{}”: {} auto-applied user(s), {} unapplied user(s), and {} enrolled user(s) (could not be altered)".format(
                        "”, “".join(
                            [x[0] for x in updated_fields],
                        ),
                        affected_counts["applied_users"],
                        affected_counts["removed_users"],
                        affected_counts["ignored_users"],
                    )
                    log.info(
                        "{} (view_only={})".format(
                            # Remove the unicode quotes when logging
                            user_message.replace("“", '"').replace("”", '"'),
                            view_only,
                        ),
                        function="IQProgramRefAdmin.get_changes",
                        user_id=request.user.id,
                    )
                    self.message_user(
                        request,
                        user_message,
                        messages.SUCCESS,
                    )

        return affected_users

    # Add custom buttons to the save list in the admin template (from
    # https://stackoverflow.com/a/34899874/5438550 and
    # https://stackoverflow.com/a/69487616/5438550)
    change_form_template = "admin/custom_button_change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # Add any custom buttons. This must be a list/tuple of list/tuples, as
        # (name, url). The 'url' portion must match the
        # "if 'url' in request.POST:" section of response_change()
        extra_context["custom_buttons"] = [
            {
                "title": "View Changes",
                "link": "_view_changes",
            },
        ]

        opts = self.model._meta
        pk_value = object_id
        preserved_filters = self.get_preserved_filters(request)
        if "_view_changes_complete" in request.POST:
            # If 'View Changes' was selected, refresh the page via a redirect
            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    "preserved_filters": preserved_filters,
                    "opts": opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=extra_context,
        )

    def response_change(self, request, obj):
        if "_view_changes" in request.POST:
            # Set the current_app for the admin base template
            request.current_app = self.admin_site.name
            return render(
                request,
                "admin/open_view_changes.html",
                {
                    # Set some page-specific text
                    "site_header": "Get FoCo administration",
                    "title": "Calculating proposed changes in new window...",
                    "site_title": "Get FoCo administration",
                },
            )

        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        if "_view_changes" in request.POST:
            # Run the logic for changes
            affected_users = self.get_changes(request, obj, form, change)

            # Set a session var with the affected users
            request.session["permissive_user_ids"] = [
                x.id for x in affected_users["permissive"]
            ]
            request.session["restrictive_user_ids"] = [
                x.id for x in affected_users["restrictive"]
            ]

            # Set a session var with the altered fields
            request.session["altered_fields"] = [
                (x, form.initial[x], form.cleaned_data[x]) for x in form.changed_data
            ]

        else:
            # If 'View Changes' was not selected, save the model (with
            # message(s) to the user). The model must be saved first in order
            # to properly apply/remove programs
            super().save_model(request, obj, form, change)

            # Make the changes after saving the model
            _ = self.get_changes(request, obj, form, change, view_only=False)


class EligibilityProgramRefForm(forms.ModelForm):
    class Meta:
        model = EligibilityProgramRef

        fields = [
            "program_name",
            "ami_threshold",
            "is_active",
            "friendly_name",
            "friendly_description",
        ]

        # Override the widgets for description field
        widgets = {
            "friendly_description": Textarea,
        }


class IQProgramRefForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()

        # Raise a ValidationError on the form if there isn't at least one True
        # `requires_` field
        if not any(cleaned_data.get(x[0]) for x in get_iqprogram_requires_fields()):
            msg = ValidationError(
                _(
                    "At least one 'Requires' box must be checked (otherwise any address anywhere is eligible).",
                ),
                code="invalid",
            )
            for fd, x in get_iqprogram_requires_fields():
                self.add_error(fd, msg)

    class Meta:
        model = IQProgramRef

        req_fields = get_iqprogram_requires_fields()

        program_fields = [
            "program_name",
            "ami_threshold",
            "is_active",
            "enable_autoapply",
            "renewal_interval_year",
        ]
        display_fields = [
            "friendly_name",
            "friendly_category",
            "friendly_description",
            "friendly_supplemental_info",
            "learn_more_link",
            "friendly_eligibility_review_period",
            "additional_external_form_link",
        ]
        address_fields = [x[0] for x in req_fields]

        fields = program_fields + display_fields + address_fields

        # Override the widgets for description field
        widgets = {
            "friendly_description": Textarea,
        }

        # Override the labels for the 'requires_' fields to capitalize the first
        # word and place single quotes around the field name
        labels = {}
        for req, x in req_fields:
            label_list = req.capitalize().split("_")

            # Insert single quotes at the beginning and end of the field name
            label_list[1] = f"'{label_list[1]}"
            label_list[-1] = f"{label_list[-1]}'"

            labels[req] = " ".join(label_list)
