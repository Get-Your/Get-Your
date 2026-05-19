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
from django.contrib.auth.password_validation import validate_password
from app.models import Household
from ref.models import Address as AddressRef
from get_your.users.models import User
from django.forms import BaseFormSet

from app.backend.address import validate_usps

from phonenumber_field.widgets import RegionalPhoneNumberWidget

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
        fields = ['address1', 'address2', 'city', 'state', 'zip_code', 'address_sha1']
        labels = {
            'address1': 'Street Address',
            'address2': 'Apt, Suite, etc.',
            'city': 'City',
            'state': 'State',
            'zip_code': 'Zip Code',
            'address_sha1': ''
        }
        widgets = {
            'address1': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 200}),
            'address2': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 200}),
            'city': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 64}),
            'state': forms.TextInput(attrs={'class':'form-control shadow-sm', 'maxlength': 2}),
            'zip_code': forms.NumberInput(attrs={'class':'form-control shadow-sm', 'max': 99999}),
            'address_sha1': forms.HiddenInput()
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
        model = Household
        fields = ['user', 'rent_own', 'duration_at_address']
        labels = {
            'user': ''
        }
        widgets = {
            'user': forms.HiddenInput(),
            'rent_own': forms.Select(attrs={'class':'form-select shadow-sm'}),
            'duration_at_address': forms.Select(attrs={'class':'form-select shadow-sm'})
        }

class BaseAddressFormSet(BaseFormSet):
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


AddressFormSet = forms.formset_factory(
    AddressForm,
    extra=1,
    min_num=1,
    max_num=2,
    validate_min=True,
    formset=BaseAddressFormSet
)
