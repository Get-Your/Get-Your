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

from django import forms
from django.contrib.auth import get_user_model

from ref.models import Address as AddressRef

from .constants import duration_at_address_choices
from .constants import rent_own_choices
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
    rent_own = forms.ChoiceField(choices=rent_own_choices, widget=forms.RadioSelect())

    duration_at_address = forms.ChoiceField(
        choices=duration_at_address_choices,
        widget=forms.RadioSelect(),
    )

    class Meta:
        model = Household
        fields = [
            "rent_own",
            "duration_at_address",
            "number_persons_in_household",
        ]
        labels = {
            "rent_own": "Do you rent or own your current residence?",
            "duration_at_address": "How long have you lived at this address?",
            "number_persons_in_household": "How many individuals are in your household?",
        }


class DateInput(forms.DateInput):
    input_type = "date"


class HouseholdMembersForm(forms.ModelForm):
    name = forms.CharField(label="First & Last Name of Individual")
    birthdate = forms.DateField(
        label="Their Birthdate",
        widget=forms.widgets.DateInput(attrs={"type": "date"}),
    )
    identification_path = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = HouseholdMembers
        fields = [
            "name",
            "birthdate",
            "identification_path",
        ]


class AddressLookupForm(forms.Form):
    address = forms.CharField(label="Address")
