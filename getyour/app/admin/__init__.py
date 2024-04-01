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
    IQProgram,
)
from app.backend.address import address_check
from app.backend.finalize import finalize_address, finalize_application
from app.constants import application_pages
from app.forms import UserUpdateForm
from app.admin.list_filters import (
    GMAListFilter,
    CityCoveredListFilter,
    NeedsVerificationListFilter,
)


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

    readonly_fields = [
        'created_at',
        'modified_at',
        'mailing_addr',
        'eligibility_addr',
    ]
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'created_at',
                    'modified_at',
                    'mailing_addr',
                    'eligibility_addr',
                ],
            },
        ),
    ]

    @admin.display(description='mailing address')
    def mailing_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.mailing_address_id)
        if addr.address2 == '':
            return format_html(
                f'<a href="/admin/app/addressrd/{addr.id}/change">{addr.address1}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )
        else:
            return format_html(
                f'<a href="/admin/app/addressrd/{addr.id}/change">{addr.address1}<br />{addr.address2}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )

    @admin.display(description='eligibility address')
    def eligibility_addr(self, obj):
        addr = AddressRD.objects.get(id=obj.eligibility_address_id)
        if addr.address2 == '':
            return format_html(
                f'<a href="/admin/app/addressrd/{addr.id}/change">{addr.address1}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )
        else:
            return format_html(
                f'<a href="/admin/app/addressrd/{addr.id}/change">{addr.address1}<br />{addr.address2}<br />{addr.city}, {addr.state} {addr.zip_code}</a>'
            )

    # Show zero extra (unfilled) options
    extra = 0


class HouseholdInline(admin.TabularInline):
    model = Household
    
    fk_name = "user"

    fieldsets = [
        (
            None,
            {
                'fields': [
                    'created_at',
                    'modified_at',
                    'duration_at_address',
                    'rent_own',
                    'number_persons_in_household',
                    'income_percent',
                    'is_income_verified',
                ],
            },
        ),
    ]

    def get_readonly_fields(self, request, obj):
        """
        Return readonly fields based on user type and groups. Note that groups
        is looking for inclusion and is hierarchical (the most permissive is
        first).
        
        """

        # Global readonly fields
        readonly_fields = [
            'created_at',
            'modified_at',
        ]
        if request.user.is_superuser:
            # No extra readonly fields for superuser
            pass
        elif request.user.groups.filter(
            name__istartswith='income'
        ).exists():
            # Add these fields as read-only if the user is in a group whose name
            # starts with case-insensitive 'income'
            readonly_fields.extend([
                'rent_own',
                'duration_at_address',
                'number_persons_in_household',
            ])
        # Ensure @property and calculated fields displayed here are always
        # marked read-only. Note that duplicates are removed later, so no need
        # to check here
        static_fields = ['income_percent']
        readonly_fields.extend(static_fields)
        # Ensure there are no duplicates
        return list(set(readonly_fields))

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

    @admin.display(description='program name')
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


class UserAdmin(admin.ModelAdmin):
    search_fields = ('last_name__startswith', 'first_name__startswith', 'email')
    list_display = ('last_name', 'first_name', 'email', 'last_completed_at')
    ordering = (Lower('last_name'), Lower('first_name'))    # case-insensitive
    list_display_links = ('email', )
    list_filter = (NeedsVerificationListFilter, )
    date_hierarchy = 'last_completed_at'

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

    def get_fieldsets(self, request, obj):
        """
        Return fieldsets based on user type. All users get the default fieldset,
        then additional fields are added for superusers.
        
        """

        fieldsets = [
            (
                'USER',
                {
                    'fields': [
                        'full_name',
                        'email',
                        'phone_number',
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
    
    # def get_formset_kwargs(self, request, obj, inline, prefix):
    #     return {
    #         **super().get_formset_kwargs(request, obj, inline, prefix),
    #         "form_kwargs": {"request": request},
    #     }

    # def get_form(self, request, obj=None, **kwargs):
    #     if not request.user.is_superuser:
    #         kwargs["form"] = UserUpdateForm
    #     return super().get_form(request, obj, **kwargs)
    
    # exclude = ('date_joined',)
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
        static_fields = ['full_name', 'renewal_action_parsed']
        readonly_fields.extend(static_fields)
        # Ensure there are no duplicates
        return list(set(readonly_fields))

    inlines = [
        AddressInline,
        HouseholdInline,
        HouseholdMembersInline,
        EligibilityProgramInline,
        IQProgramInline,
    ]

    list_per_page = 100


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

        # If the input_object is not a QuerySet, coerce it into a list so for
        # similar operation
        if isinstance(input_object, QuerySet):
            queryset = input_object
        else:
            queryset = [input_object]

        # Loop through the queryset (or similated queryset)
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
                finalize_address(obj, is_in_gma, has_connexion)

                # Loop through any users with this as their eligibility address
                # and correct their application if they have already completed it
                for addr in obj.eligibility_user.all():
                    if addr.user.last_completed_at is not None:
                        _ = finalize_application(addr.user, update_user=False)


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
        return super(AddressAdmin, self).change_view(
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
                'admin:%s_%s_change' % (opts.app_label, opts.model_name),
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
