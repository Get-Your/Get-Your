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
from app.constants import rent_own_choices, duration_at_address_choices
from ref.models import Address as AddressRef
from get_your.users.models import User

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
            'phone_number': forms.TelInput(attrs={'class':'form-control shadow-sm'})
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
            'zip_code': forms.NumberInput(attrs={'class':'form-control shadow-sm', 'max': 99999})
        }

class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ['rent_own', 'duration_at_address']
        widgets = {
            'rent_own': forms.Select(attrs={'class':'form-select shadow-sm'}),
            'duration_at_address': forms.Select(attrs={'class':'form-select shadow-sm'})
        }
