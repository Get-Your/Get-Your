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
from django import forms
from django.contrib.auth.password_validation import validate_password
from app.models import HouseholdMembers, User, Household, AddressRD, EligibilityProgram, Feedback
from app.constants import rent_own_choices, duration_at_address_choices


class UserForm(forms.ModelForm):
    password2 = forms.CharField(label='Enter Password Again',
                                widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number',
                  'password']  # password between email and phone number
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'password': 'Password',
            'email': 'Email',
            'phone_number': 'Phone Number',
        }

    def passwordCheck(self):
        password = self.cleaned_data['password']
        try:
            validate_password(password, user=None, password_validators=None)
        except Exception as e:
            return str(e)

    def passwordCheckDuplicate(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            return 'Passwords don\'t match.'
        return cd['password']

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        user.set_password(user.password)  # set password properly before commit
        if commit:
            user.save()
        return user


# form for user account creation
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone_number': 'Phone Number',
        }

    # Save function that will update the user's
    # first name, last name, email, and phone number
    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit=False)
        if commit:
            user.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = AddressRD
        fields = ['address1', 'address2', 'city', 'state', 'zip_code']
        labels = {
            'address1': 'Street Address',
            'address2': 'Apt, Suite, etc.',
            'city': 'City',
            'state': 'State',
            'zip_code': 'Zip Code',
        }


class HouseholdForm(forms.ModelForm):
    
    rent_own = forms.ChoiceField(
        choices=rent_own_choices, widget=forms.RadioSelect())

    duration_at_address = forms.ChoiceField(
        choices=duration_at_address_choices, widget=forms.RadioSelect())

    class Meta:
        model = Household
        fields = ['rent_own', 'duration_at_address',
                  'number_persons_in_household',]
        labels = {
            'rent_own': 'Do you rent or own your current residence?',
            'duration_at_address': 'How long have you lived at this address?',
            'number_persons_in_household': 'How many individuals are in your household?',
        }


class DateInput(forms.DateInput):
    input_type = 'date'


class HouseholdMembersForm(forms.ModelForm):
    name = forms.CharField(label='First & Last Name of Individual')
    birthdate = forms.DateField(
        label="Their Birthdate", widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    identification_path = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = HouseholdMembers
        fields = ['name', 'birthdate', 'identification_path', ]


class AddressLookupForm(forms.Form):
    address = forms.CharField(label='Address')


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = EligibilityProgram
        fields = ['id', 'document_path',]
        widgets = {
            'document_path': forms.ClearableFileInput(attrs={'multiple': True}),
        }


class FeedbackForm(forms.ModelForm):
    feedback_comments = forms.CharField(max_length=500, required=False)
    star_rating = forms.CharField(max_length=1, required=False)

    class Meta:
        model = Feedback
        fields = ['feedback_comments', 'star_rating']
        labels = {
            'star_rating': 'Rating in Stars',
            'feedback_comments': 'Feedback and Comments by Clients',
        }
