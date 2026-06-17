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
