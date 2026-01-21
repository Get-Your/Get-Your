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

import pendulum
from django import forms
from django.contrib.auth import get_user_model
from formset.collection import FormCollection
from formset.renderers.bootstrap import FormRenderer
from formset.utils import FormMixin
from formset.widgets import UploadedFileInput

from ref.models import Address as AddressRef

from .constants import duration_at_address_choices
from .constants import rent_own_choices
from .constants import supported_content_types
from .models import Household
from .models import HouseholdMembers

# Get the user model
User = get_user_model()


class AddressForm(forms.ModelForm):
    class Meta:
        model = AddressRef
        fields = ["address1", "address2", "city", "state", "zip_code"]
        labels = {
            "address1": "Street Address",
            "address2": "Apt, Suite, etc.",
            "city": "City",
            "state": "State",
            "zip_code": "Zip Code",
        }


class HouseholdForm(forms.ModelForm):
    rent_own = forms.ChoiceField(
        label="Do you rent or own your current residence?",
        choices=rent_own_choices,
        widget=forms.RadioSelect,
    )

    duration_at_address = forms.ChoiceField(
        label="How long have you lived at this address?",
        choices=duration_at_address_choices,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Household
        fields = [
            "rent_own",
            "duration_at_address",
        ]
        labels = {
            "rent_own": "Do you rent or own your current residence?",
            "duration_at_address": "How long have you lived at this address?",
        }


class DateInput(forms.DateInput):
    input_type = "date"


class HouseholdMembersForm(forms.ModelForm):
    """Form for user-input 'individuals in household' data."""

    # Create (hidden) field to track objects in this form
    id = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    class Meta:
        model = HouseholdMembers
        fields = [
            "id",
            "full_name",
            "birthdate",
            "identification_path",
        ]
        labels = {
            "full_name": "First & Last Name of Individual",
            "birthdate": "Their Birthdate",
            "identification_path": "Upload ID",
        }
        widgets = {
            "birthdate": DateInput(attrs={"type": "date"}),
            "identification_path": UploadedFileInput(
                attrs={
                    "accept": ", ".join(set(supported_content_types.values())),
                },
            ),
        }


class HouseholdMembersFormCollection(FormCollection):
    """
    Form Collection to allow users to add/remove 'siblings' to define each
    individuals in their household.

    """

    default_renderer = FormRenderer(
        field_css_classes="mb-0",
        collection_css_classes="mb-0 col-12",
    )

    person = HouseholdMembersForm()
    legend = "Tell us about the individuals in your household"
    min_siblings = 1  # minimum number that are required
    add_label = "Add another person"
    related_field = "household"
    is_sortable = True

    def retrieve_instance(self, data):
        if data := data.get("person"):
            try:
                return self.instance.members.get(id=data.get("id") or 0)
            except (AttributeError, HouseholdMembers.DoesNotExist, ValueError):
                return HouseholdMembers(
                    household=self.instance,
                    full_name=data.get("full_name"),
                    birthdate=pendulum.parse(data.get("birthdate")).date(),
                    identification_path=data.get("identification_path"),
                )


class HouseholdFormCollection(FormCollection, FormMixin):
    """
    Form Collection to render the 'household' and 'individuals in household' on
    a single page.

    """

    default_renderer = FormRenderer(
        field_css_classes="col-12",
        fieldset_css_classes="col-12",
    )
    household = HouseholdForm()
    # Note that the linked collections must be defined with the related_name to
    # the parent model
    members = HouseholdMembersFormCollection()


class AddressLookupForm(forms.Form):
    address = forms.CharField(label="Address")
