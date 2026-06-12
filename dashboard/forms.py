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
from django import forms

from ref.models import AddressRef
from app.models import HouseholdMembers
from get_your.users.models import User
from django.forms import BaseModelFormSet

from app.backend.address import validate_usps
from app.constants import supported_content_types

from phonenumber_field.widgets import RegionalPhoneNumberWidget
from django.forms.widgets import ClearableFileInput

class CustomClearableFileInput(ClearableFileInput):
    clear_checkbox_label = "Remove"
    initial_text = "Current File"
    input_text = "Upload a New File"
    # Path to your new custom HTML snippet
    template_name = 'widgets/custom_clearable_file_input.html'

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone_number': 'Phone Number',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control shadow-sm'}),
            'last_name': forms.TextInput(attrs={'class':'form-control shadow-sm'}),
            'email': forms.EmailInput(attrs={'class':'form-control shadow-sm'}),
            'phone_number': RegionalPhoneNumberWidget(attrs={'class':'form-control shadow-sm'})
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = AddressRef
        fields = ['address1', 'address2', 'city', 'state', 'zip_code']
        labels = {
            'address1': 'Street Address',
            'address2': 'Apt, Suite, etc.',
            'city': 'City',
            'state': 'State',
            'zip_code': 'Zip Code',
        }
        widgets = {
            'address1': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 200}),
            'address2': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 200}),
            'city': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 64}),
            'state': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 2}),
            'zip_code': forms.NumberInput(attrs={'class':'form-control shadow-sm', 'max': 99999}),
        }

class SameAddressForm(forms.Form):
    mailing_address_same_as_home = forms.ChoiceField(
        choices=(
            ('yes', 'Yes'),
            ('no', 'No')
        ),
        initial='yes',
        widget=forms.RadioSelect(attrs={'class':'form-check-input shadow-sm'})
    )

class HouseholdForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['rent_own', 'duration_at_address']
        widgets = {
            'rent_own': forms.Select(attrs={'class':'form-select shadow-sm'}),
            'duration_at_address': forms.Select(attrs={'class':'form-select shadow-sm'})
        }

class HouseholdMembersForm(forms.ModelForm):
    class Meta:
        model = HouseholdMembers
        fields = ['id', 'user', 'full_name', 'birthdate', 'identification_path']
        labels = {
            'id': '',
            'user': '',
            'full_name': 'Full Name',
            'birthdate': 'Birth Date',
            'identification_path': 'Upload Id'
        }
        widgets = {
            'id': forms.HiddenInput(),
            'user': forms.HiddenInput(),
            'full_name': forms.TextInput(
                attrs={'class':'form-control shadow-sm', 'maxlength': 100}
            ),
            'birthdate': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class':'form-control shadow-sm'}
            ),
            'identification_path': CustomClearableFileInput(
                attrs={
                    'class':'form-control shadow-sm',
                    'accept': ', '.join(supported_content_types.values())
                }
            )
        }

class BaseAddressFormSet(BaseModelFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.index = index

    def clean(self):
        """Checks that address is valid with USPS API"""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        for form in self.forms:
            # there will only ever be two address forms total
            # in the set. the first form represents eligibility address
            # and should always have data, but mailing address may be empty
            if form.cleaned_data:
                # can check USPS and whatever else here
                corrected_address = validate_usps(form.cleaned_data)
                if 'error' in corrected_address:
                    form.add_error('address1', corrected_address['error']['message'])

class BaseHouseholdMembersFormSet(BaseModelFormSet):

    def clean(self):
        """Return with input on error"""
        if any(self.errors):
            print(self.errors)
            # Don't bother validating the formset unless each form is valid on its own
            return


HouseholdMembersFormSet = forms.modelformset_factory(
    HouseholdMembers,
    HouseholdMembersForm,
    extra=0,
    min_num=1,
    max_num=8,
    can_delete=True,
    validate_min=True,
    formset=BaseHouseholdMembersFormSet
)

AddressFormSet = forms.modelformset_factory(
    AddressRef,
    AddressForm,
    extra=1,
    min_num=1,
    max_num=2,
    validate_min=True,
    formset=BaseAddressFormSet
)
