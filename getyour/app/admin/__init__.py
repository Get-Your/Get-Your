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

from django.shortcuts import render
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ngettext
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import reverse
from django.db.models.functions import Lower
from django.db.models.query import QuerySet
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.http import HttpResponseRedirect

from app.models import (
    User,
    Address,
    AddressRD,
    Household,
    HouseholdMembers,
    EligibilityProgram,
    EligibilityProgramRD,
    IQProgram,
    Admin,
)
from app.backend import get_eligible_iq_programs, get_iqprogram_required_fields
from app.backend.address import address_check
from app.backend.finalize import (
    finalize_address,
    finalize_application,
    remove_ineligible_programs,
)
from app.constants import application_pages
from app.forms import UserUpdateForm
from app.admin.filters import (
    GMAListFilter,
    CityCoveredListFilter,
    NeedsVerificationListFilter,
    needs_income_verification_filter,
)
from app.admin.forms import ProgramChangeForm, ProgramAddForm

from logger.wrappers import LoggerWrapper


# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


# Customize admin site text

# Text to put at the end of each page's <title>
admin.site.site_title = 'Get FoCo administration'

# Text to put in each page's <h1> (and above login form)
admin.site.site_header = 'Get FoCo administration'

# Text to put at the top of the admin index page and in the page header
admin.site.index_title = 'Admin menu'


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


def document_path_parsed(obj):
    """
    Parse each document_path into a link that can be used to view the
    files.

    This function spoofs the URLs that ``django-storages`` creates
    automatically; this could be eliminated (except for the headers) if the
    data model was updated to save one file per record.
    
    """
    # Parse the stringified list of document_path values. Dynamically
    # converting to a list would be dangerous, so this is processed manually.
    if obj.document_path.name != '':
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
    else:
        url_list = ['No document available']

    # return format_html(url_list[0])
    return format_html('<br />'.join(url_list))


def get_admin_url(obj, urltype='change'):
    """
    Return the admin URL of the specific object.
    
    Uses the built-in URL patterns documented at
    https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#reversing-admin-urls.
    
    """
    return reverse(
        "admin:{al}_{md}_{tp}".format(
            al=obj._meta.app_label,
            md=obj._meta.model_name,
            tp=urltype,
        ),
        args=(obj.id,),
    )


class AddressInline(admin.TabularInline):
    model = Address
    
    fk_name = "user"

    fields = readonly_fields = [
        'created_at',
        'modified_at',
        'mailing_addr',
        'eligibility_addr',
    ]

    @admin.display(description='mailing address')
    def mailing_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.mailing_address_id)
        if addr.address2 == '':
            return format_html(
                f'<a href="{get_admin_url(addr)}">{addr.address1}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )
        else:
            return format_html(
                f'<a href="{get_admin_url(addr)}">{addr.address1}<br />{addr.address2}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )

    @admin.display(description='eligibility address')
    def eligibility_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.eligibility_address_id)
        if addr.address2 == '':
            return format_html(
                f'<a href="{get_admin_url(addr)}">{addr.address1}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )
        else:
            return format_html(
                f'<a href="{get_admin_url(addr)}">{addr.address1}<br />{addr.address2}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )

    # Show zero extra (unfilled) options
    extra = 0


class HouseholdInline(admin.TabularInline):
    model = Household
    
    fk_name = "user"

    fields = [
        'created_at',
        'modified_at',
        'duration_at_address',
        'rent_own',
        'number_persons_in_household',
        'income_percent',
        'is_income_verified',
    ]

    def get_readonly_fields(self, request, obj):
        """
        Return readonly fields based on user type and groups. Note that this
        follows zero-trust; it starts with all fields read-only and removes them
        based on permissions.
        
        """

        # Global readonly fields
        readonly_fields = [
            'created_at',
            'modified_at',
            'email_address',
            'phone_number',
            'rent_own',
            'duration_at_address',
            'number_persons_in_household',
        ]
        # Ensure @property and calculated fields displayed here are always
        # marked read-only
        static_fields = ['income_percent']
        readonly_fields.extend(static_fields)

        readonly_remove = []
        if request.user.is_superuser:
            # Remove the following readonly fields for superusers
            readonly_remove.extend([
                'email_address',
                'phone_number',
                'rent_own',
                'duration_at_address',
                'number_persons_in_household',
            ])
        elif request.user.groups.filter(
            name__istartswith='income'
        ).exists():
            # Remove these fields from read-only if the user is in the
            # 'income...' group
            readonly_remove.extend([
                'email_address',
                'phone_number',
            ])
        
        # Remove the fields and re-listify
        return list(set(readonly_fields) - set(readonly_remove))

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

    fields = readonly_fields = [
        'created_at',
        'modified_at',
        'household_info_parsed',
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
                if 'identification_path' in itm and itm['identification_path'] is not None:
                    document_link = """<a href="{trg}" onclick="javascript:window.open(this.href, 'newwindow', 'width=600, height=600'); return false;">View Identification</a>""".format(
                        trg=reverse(
                            'app:admin_view_file',
                            kwargs={'blob_name': itm['identification_path']},
                        ),
                    )
                else:
                    document_link = "No identification available"
                person_list.append(document_link)
                person_list.append('')

        return format_html('<br />'.join(person_list))

    # Show zero extra (unfilled) options
    extra = 0


class EligibilityProgramInline(admin.TabularInline):
    def get_queryset(self, request):
        """ Override ordering to use program friendly name instead. """
        qs = super().get_queryset(request)
        qs = qs.order_by('program__friendly_name')
        return qs

    model = EligibilityProgram

    fk_name = "user"

    fields = readonly_fields = [
        'created_at',
        'modified_at',
        'program_name',
        'record_edit',
        'display_document_link',
    ]

    @admin.display(description='program name')
    def program_name(self, obj):
        return obj.program.friendly_name
    
    @admin.display(description='edit record')
    def record_edit(self, obj):
        # Record can only be edited if is_income_verified is False
        if obj.user.household.is_income_verified is False:
            return format_html(
                f'<a href="{get_admin_url(obj)}">Edit Record</a>'
            )
        else:
            return "Cannot Be Edited"

    @admin.display(description='document')
    def display_document_link(self, obj):
        """ Display a link to each document. """
        return document_path_parsed(obj)

    # Show zero extra (unfilled) options
    extra = 0


class IQProgramInline(admin.TabularInline):
    def get_queryset(self, request):
        """ Override ordering to use program friendly name instead. """
        qs = super().get_queryset(request)
        qs = qs.order_by('program__friendly_name')
        return qs

    model = IQProgram

    fk_name = "user"

    fields = readonly_fields = [
        'program_name',
        'applied_at',
        'enrollment_status',
    ]

    @admin.display(description='program name')
    def program_name(self, obj):
        return obj.program.friendly_name

    @admin.display(description='enrolled at')
    def enrollment_status(self, obj):
        if obj.is_enrolled:
            ts = pendulum.instance(obj.enrolled_at)
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


class AdminInline(admin.StackedInline):
    model = Admin
    
    fk_name = "user"

    fields = ['awaiting_user_response']

    # Show zero extra (unfilled) options
    extra = 0


class UserAdmin(admin.ModelAdmin):
    search_fields = ('last_name__startswith', 'first_name__startswith', 'email')
    list_display = ('last_name', 'first_name', 'email', 'last_completed_at')
    ordering = (Lower('last_name'), Lower('first_name'))    # case-insensitive
    list_display_links = ('email', )
    list_filter = (NeedsVerificationListFilter, )
    date_hierarchy = 'last_completed_at'
    actions = ('mark_verified', 'mark_awaiting_response')

    @admin.display(description='last renewal action')
    def renewal_action_parsed(self, obj):
        if obj.last_renewal_action is not None:
            status_list = ['Remaining steps:', '']
            # Output the uncompleted pages in application page order. Include if
            # key DNE in last_renewal_action or status is not 'completed'
            status_list.extend([
                key.replace('_', ' ').title() for key in application_pages.keys() \
                    if key not in obj.last_renewal_action.keys() or \
                    obj.last_renewal_action[key].get('status')!='completed'
            ])

            return '\n'.join(status_list)
        else:
            return self.get_empty_value_display()
        
    @admin.display(description='message to user')
    def user_message(self, obj):
        msg = []
        # Get the user's eligibility address
        eligibility_address = AddressRD.objects.filter(
            id=obj.address.eligibility_address_id
        ).first()

        # Notify if the user is not qualified for any programs
        if len(get_eligible_iq_programs(obj, eligibility_address)) == 0:
            msg.append("User is not eligible for any programs.")

            # If the user doesn't qualify for any programs, check if the user's
            # address doesn't have a required component
            req_fields = get_iqprogram_required_fields()
            # The second element holds the field requirements in AddressRD
            for req, fd in req_fields:
                if not getattr(eligibility_address, fd):
                    msg[-1] += f" User's address has False `{fd}`; IQ Programs may require it to be True (see `{req}`)."

        # Notify if the user is archived
        if obj.is_archived:
            msg.append("User account is disabled ('is archived').")

        if len(msg) > 0:
            return "- {}".format('\n- '.join(msg))
        else:
            return self.get_empty_value_display()
        
    def has_income_verification_permission(self, request, obj=None):
        # Define income_verification permissions
        if request.user.is_superuser or request.user.groups.filter(
            name__istartswith='income'
        ).exists():
            return True
        return False

    def get_fieldsets(self, request, obj):
        """
        Return fieldsets based on user type. All users get the default fieldset,
        then additional fields are added for superusers.
        
        """

        # Log entrance to this changelist. This attempts to track called
        # functions
        log.info(
            "Entering admin changelist",
            function='UserAdmin',
            user_id=request.user.id,
        )

        fieldsets = [
            (
                'USER',
                {
                    'fields': [
                        'full_name',
                        'email',
                        'phone_number',
                        'user_message',
                        'id',
                        'is_archived',
                    ],
                },
            ),
            (
                'APPLICATION',
                {
                    'fields': [
                        'date_joined',
                        'last_login',
                        'last_completed_at',
                        'last_action_notification_at',
                        # 'last_application_parsed',
                        'renewal_action_parsed',
                    ],
                },
            ),
        ]

        if request.user.is_superuser:
            for idx, elem in enumerate(fieldsets):
                if elem[0] == 'USER':
                    fieldsets[idx][1]['fields'].extend([
                        'first_name',
                        'last_name',
                        'is_active',
                        'is_staff',
                        'is_superuser',
                        'groups',
                    ])
                elif elem[0] == 'APPLICATION':
                    fieldsets[idx][1]['fields'].extend([
                        'has_viewed_dashboard',
                    ])

        return fieldsets

    def get_form(self, *args, **kwargs):
        # Use this function to add help_text to the display-only fields
        help_texts = {
            'renewal_action_parsed': "The uncompleted steps in a user's renewal flow. An empty value indicates the user is not mid-renewal.",
            'user_message': "Message to the user regarding their application or account. Aspects shown here may not yet be available to the user.",
        }
        kwargs.update({'help_texts': help_texts})
        return super().get_form(*args, **kwargs)

    def get_readonly_fields(self, request, obj):
        """
        Return readonly fields based on user type and groups. Note that groups
        is looking for inclusion and is hierarchical (the most permissive is
        first).
        
        """

        # Global readonly fields
        readonly_fields = [
            'id',
            'date_joined',
            'last_login',
            'has_viewed_dashboard',
            'last_action_notification_at',
        ]
        if request.user.is_superuser:
            # No extra readonly fields for superuser
            pass
        elif request.user.groups.filter(
            name__istartswith='income'
        ).exists():
            # Add these fields as read-only if the user is in a group whose name
            # starts with case-insensitive 'income'
            readonly_fields.extend(['first_name', 'last_name', 'last_completed_at'])
        # Ensure @property and calculated fields displayed here are always
        # marked read-only. Note that duplicates are removed later, so no need
        # to check here
        static_fields = [
            'full_name',
            'renewal_action_parsed',
            'user_message',
        ]
        readonly_fields.extend(static_fields)
        # Ensure there are no duplicates
        return list(set(readonly_fields))

    inlines = [
        AdminInline,
        AddressInline,
        HouseholdInline,
        HouseholdMembersInline,
        EligibilityProgramInline,
        IQProgramInline,
    ]

    @admin.action(
        description="Mark selected users as 'awaiting response'",
    )
    def mark_awaiting_response(self, request, queryset):
        # Mark the selected users as 'awaiting response', which will hide them
        # from the 'new' needs verification filter

        log.info(
            "Entering admin action",
            function='mark_awaiting_response',
            user_id=request.user.id,
        )

        # Create Admin queryset of the same users and update the field
        Admin.objects.filter(
            user__in=[usr for usr in queryset]
        ).update(
            awaiting_user_response=True
        )

    @admin.action(
        # Only allow this action with 'income_verification' permissions
        permissions=['income_verification'],
        description="Mark selected users as 'income verified'",
    )
    def mark_verified(self, request, queryset):
        # Mark the selected users verified, but only if they meet the 'needs
        # income verification' criteria

        # Log entrance to this action. This attempts to track called
        # functions
        log.info(
            "Entering admin action",
            function='mark_verified',
            user_id=request.user.id,
        )

        check_queryset = needs_income_verification_filter(queryset)

        # check_queryset is a potentially-further-filtered queryset. If their
        # lengths are the same, mark 'income verified'; else return an error msg
        if len(queryset) == len(check_queryset):
            # Note that queryset.update() cannot be used here, since the update
            # is on a related model; instead, loop through queryset and update
            # each related model (in order to avoid .save() calls)
            for usr in queryset:
                Household.objects.filter(
                    user=usr
                ).update(
                    is_income_verified=True
                )

            log.info(
                f"{len(queryset)} users marked as verified.",
                function='mark_verified',
                user_id=request.user.id,
            )
            
            # Add a message to the user when complete
            self.message_user(request, ngettext(
                'Income was verified for %d user.',
                'Income was verified for %d users.',
                len(queryset),
            ) % len(queryset), messages.SUCCESS)

        else:
            # Add an error message to the user
            error_count = len(queryset) - len(check_queryset)

            log.error(
                f"Not all users are applicable (only {len(check_queryset)} of the {len(queryset)} selected could have been verified).",
                function='mark_verified',
                user_id=request.user.id,
            )

            self.message_user(request, ngettext(
                'Cancelled: the user is not applicable for income verification.',
                'Cancelled: not all users are applicable for income verification.',
                error_count,
            ), messages.ERROR)

    list_per_page = 100

    # Add custom buttons to the save list in the admin template (from
    # https://stackoverflow.com/a/34899874/5438550 and
    # https://stackoverflow.com/a/69487616/5438550)
    change_form_template = 'admin/custom_button_change_form.html'
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        # Add any custom buttons. This must be a list/tuple of list/tuples, as
        # (name, url). The 'url' portion must match the
        # "if 'url' in request.POST:" section of response_change()

        # Programs can be added at any time
        extra_context['custom_buttons'] = [
            ('Add IQ Program', '_add_program'),
        ]

        opts = self.model._meta
        pk_value = object_id
        preserved_filters = self.get_preserved_filters(request)
        if '_add_program_submit' in request.POST:
            # Handle 'Update Program' after 'submit' has been selected
            form = ProgramAddForm(object_id, request.POST)
            # form = ProgramChangeForm(request.POST)
            if form.is_valid():
                # Extract the program ID (in the 'program_name' form field) and
                # add the program to the current model
                _ = IQProgram.objects.create(
                    user_id=object_id,
                    program_id=int(form.cleaned_data['program_name']),
                )

                # Add a message to the user when complete
                self.message_user(
                    request,
                    "Successfully added the program for this user.",
                    messages.SUCCESS,
                )

            else:
                # Form is not valid; notify the user
                self.message_user(
                    request,
                    'Cancelled: something went wrong.',
                    messages.ERROR,
                )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        elif '_add_program_cancel' in request.POST:
            # User selected 'cancel'
            self.message_user(
                request,
                'Program add cancelled.',
                messages.INFO,
            )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        response = super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )
    
        # if custom_button_selected:
        #     request.method = 'POST'

        return response
    
    def response_change(self, request, obj):
        opts = self.model._meta
        pk_value = obj._get_pk_val()
        preserved_filters = self.get_preserved_filters(request)

        if "_add_program" in request.POST:
            # Handle 'Add Program': load the page to select the program name
            form = ProgramAddForm(obj.id)
            # form = ProgramChangeForm()

            # Set the current_app for the admin base template
            request.current_app = self.admin_site.name
            return render(
                request,
                'admin/program_add.html',
                {
                    'form': form,
                    # Set some page-specific text
                    'site_header': 'Get FoCo administration',
                    'title': 'Add Program',
                    'site_title': 'Get FoCo administration',
                },
            )

        elif '_add_program_submit' in request.POST:
            # Handle 'Update Program' after 'submit' has been selected
            form = ProgramAddForm(request.POST)
            # form = ProgramChangeForm(request.POST)
            if form.is_valid():
                # Extract the program ID (in the 'program_name' form field) and
                # add the program to the current model
                _ = IQProgram.objects.create(
                    user_id=obj.user.id,
                    program_id=int(form.cleaned_data['program_name']),
                )

                # Add a message to the user when complete
                self.message_user(
                    request,
                    "Successfully added the program for this user.",
                    messages.SUCCESS,
                )

            else:
                # Form is not valid; notify the user
                self.message_user(
                    request,
                    'Cancelled: something went wrong.',
                    messages.ERROR,
                )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        elif '_add_program_cancel' in request.POST:
            # User selected 'cancel'
            self.message_user(
                request,
                'Program add cancelled.',
                messages.INFO,
            )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(pk_value,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        else:
            return super().response_change(request, obj)


class AddressAdmin(admin.ModelAdmin):
    search_fields = ('address1__contains', 'address2__contains')
    list_display = ('address1', 'address2', 'is_in_gma', 'is_city_covered')
    ordering = list_display_links = ('address1', 'address2')
    list_filter = (GMAListFilter, CityCoveredListFilter)
    actions = ['update_gma']

    fields = [
        'pretty_address',
        'is_in_gma',
        'is_city_covered',
    ]

    @admin.display(description='address')
    def pretty_address(self, obj):
        if obj.address2 == '':
            return f"{obj.address1}\n{obj.city}, {obj.state} {obj.zip_code}"
        else:
            return f"{obj.address1}\n{obj.address2}\n{obj.city}, {obj.state} {obj.zip_code}"

    list_per_page = 100

    def get_readonly_fields(self, request, obj):
        """
        Return readonly fields based on GMA status.
        
        """

        # Log entrance to this changelist. This attempts to track called
        # functions
        log.info(
            "Entering admin changelist",
            function='AddressAdmin',
            user_id=request.user.id,
        )

        # Global readonly fields
        readonly_fields = [
            'pretty_address',
            'is_in_gma',
        ]
        # is_city_covered cannot be modified (from True) if is_in_gma==True
        if obj.is_in_gma:
            readonly_fields.append('is_city_covered')
        # Ensure there are no duplicates
        return readonly_fields

    @admin.action(description='Update GMA for selected addresses')
    def update_gma(self, request, input_object):
        """
        Update the GMA of the selected object(s).
        
        This is used both as a changelist action and a page-specific button, so
        ``input_object`` can be either a single object (of the modeladmin type)
        or a queryset from the changelist actions.
        
        """
        
        # Log entrance to this action. This attempts to track called
        # functions
        log.info(
            "Entering admin action",
            function='update_gma',
            user_id=request.user.id,
        )        

        # If the input_object is not a QuerySet, coerce it into a list so for
        # similar operation
        if isinstance(input_object, QuerySet):
            queryset = input_object
        else:
            queryset = [input_object]

        # Loop through the queryset (or similated queryset)
        updated_addr_count = 0
        for obj in queryset:
            # Format for address_check. All addresses in the database have been
            # through USPS, so no need to re-validate (just copy formatting)
            address_dict = {
                'AddressValidateResponse': {
                    'Address': {
                        # Note 1 & 2 are swapped
                        'Address1': obj.address2,
                        'Address2': obj.address1,
                        'City': obj.city,
                        'State': obj.state,
                        'Zip5': obj.zip_code,
                    }
                }
            }

            # Run the address check and make the final adjustments
            (is_in_gma, has_connexion) = address_check(address_dict)

            # Only make changes if there is an update
            if is_in_gma != obj.is_in_gma:
                updated_addr_count += 1
                finalize_address(obj, is_in_gma, has_connexion)

                # Loop through any users with this as their eligibility address
                # and correct their application if they have already completed it
                for addr in obj.eligibility_user.all():
                    if addr.user.last_completed_at is not None:
                        _ = finalize_application(addr.user, update_user=False)

        log.info(
            f"{len(queryset)} addresses checked; updates applied to {updated_addr_count}.",
            function='update_gma',
            user_id=request.user.id,
        )

        # Add a message to the user when complete
        self.message_user(request, ngettext(
            'GMA update was executed for %d address.',
            'GMA update was executed for %d addresses.',
            len(queryset),
        ) % len(queryset), messages.SUCCESS)

    # Add custom buttons to the save list in the admin template (from
    # https://stackoverflow.com/a/34899874/5438550 and
    # https://stackoverflow.com/a/69487616/5438550)
    change_form_template = 'admin/custom_button_change_form.html'
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        # Add any custom buttons. This must be a list/tuple of list/tuples, as
        # (name, url). The 'url' portion must match the
        # "if 'url' in request.POST:" section of response_change()
        extra_context['custom_buttons'] = [
            ('Update GMA', '_update_gma'),
        ]
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
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
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        else:
            return super().response_change(request, obj)


class EligibilityProgramAdmin(admin.ModelAdmin):
    search_fields = (
        'user__last_name__startswith',
        'user__first_name__startswith',
        'user__email__contains',
    )
    list_display = (
        'user_last_name',
        'user_first_name',
        'user_email',
        'program_name',
    )
    list_display_links = ('program_name', )
    ordering = (Lower('user__last_name'), Lower('user__first_name'))    # case-insensitive

    # def get_list_display(self, request):
    #     return None

    eligibility_fields = [
        'created_at',
        'modified_at',
        'program_name',
        'display_document_link',
    ]
    readonly_fields = eligibility_fields + ['user_email', 'full_name']

    def get_fieldsets(self, request, obj):
        """
        Return fieldsets based on user type. All users get the default fieldset,
        then additional fields are added for superusers.
        
        """

        # Log entrance to this changelist. This attempts to track called
        # functions
        log.info(
            "Entering admin changelist",
            function='EligibilityProgramAdmin',
            user_id=request.user.id,
        )

        fieldsets = [
            (
                'USER',
                {
                    'fields': [
                        'full_name',
                        'user_email',
                    ],
                },
            ),
            (
                'PROGRAM',
                {
                    'fields': self.eligibility_fields,
                },
            ),
        ]

        return fieldsets
    
    @admin.display
    def full_name(self, obj):
        return obj.user.full_name
    
    @admin.display
    def user_last_name(self, obj):
        return obj.user.last_name
    
    @admin.display
    def user_first_name(self, obj):
        return obj.user.first_name

    @admin.display
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description='program name')
    def program_name(self, obj):
        return obj.program.friendly_name
    
    @admin.display(description='document')
    def display_document_link(self, obj):
        """ Display a link to each document. """
        return document_path_parsed(obj)

    list_per_page = 100

    # Add custom buttons to the save list in the admin template (from
    # https://stackoverflow.com/a/34899874/5438550 and
    # https://stackoverflow.com/a/69487616/5438550)
    change_form_template = 'admin/custom_button_change_form.html'
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        # Add any custom buttons. This must be a list/tuple of list/tuples, as
        # (name, url). The 'url' portion must match the
        # "if 'url' in request.POST:" section of response_change()

        # Editing is disallowed once income has been verified
        obj = EligibilityProgram.objects.get(pk=object_id)
        if obj.user.household.is_income_verified is False:
            extra_context['custom_buttons'] = [
                ('Update Program', '_update_program'),
            ]

        # Intercept any POSTs from the custom button intermediate pages before
        # calling super() (so that super() only handles the following GET)
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        if '_update_program_submit' in request.POST:
            # Handle 'Update Program' after 'submit' has been selected
            form = ProgramChangeForm(request.POST)
            if form.is_valid():
                # Execute the following in a transaction so that it can be
                # rolled back if a user can't be removed from no-longer-eligible
                # programs
                try:
                    with transaction.atomic():
                        # Extract the program ID (in the 'program_name' form field) and
                        # update the current model with the new program
                        obj.program = EligibilityProgramRD.objects.get(
                            id=int(form.cleaned_data['program_name'])
                        )
                        obj.save()

                        # Finalize the user's application to update their income
                        _ = finalize_application(obj.user, update_user=False)

                        # Remove any no-longer-eligible programs
                        msg = remove_ineligible_programs(
                            obj.user,
                            income_override=obj.program.ami_threshold,
                        )

                except AttributeError as e:
                    # Undo the changes (automatic, since an exception was
                    # thrown) and notify the user
                    self.message_user(
                        request,
                        f"Program update could not be made: {e}.",
                        messages.ERROR,
                    )

                else:
                    # Add a message to the user when complete
                    self.message_user(
                        request,
                        f"Successfully updated the program for this record. {msg}",
                        messages.SUCCESS,
                    )

            else:
                # Form is not valid; notify the user
                self.message_user(
                    request,
                    'Cancelled: something went wrong.',
                    messages.ERROR,
                )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(object_id,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)
        
        elif '_update_program_cancel' in request.POST:
            # User selected 'cancel'
            self.message_user(
                request,
                'Program update cancelled.',
                messages.INFO,
            )

            redirect_url = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=(object_id,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {
                    'preserved_filters': preserved_filters,
                    'opts': opts,
                },
                redirect_url,
            )
            return HttpResponseRedirect(redirect_url)

        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )
    
    def response_change(self, request, obj):
        if "_update_program" in request.POST:
            # Handle 'Update Program': load the page to select the program name
            form = ProgramChangeForm(
                    initial={
                        "program_name": (
                            str(obj.program.id),
                            obj.program.friendly_name,
                        ),
                    },
                )

            # Set the current_app for the admin base template
            request.current_app = self.admin_site.name
            return render(
                request,
                'admin/program_change.html',
                {
                    'form': form,
                    # Set some page-specific text
                    'site_header': 'Get FoCo administration',
                    'title': 'Update Program',
                    'site_title': 'Get FoCo administration',
                },
            )

        else:
            return super().response_change(request, obj)

# Register the models

# # Create the proxy model and register it
# create_modeladmin(
#     UserAdmin,
#     name='income-verification',
#     model=User,
#     pretty_name='Income verification',
# )

admin.site.register(User, UserAdmin)
admin.site.register(AddressRD, AddressAdmin)
admin.site.register(EligibilityProgram, EligibilityProgramAdmin)
