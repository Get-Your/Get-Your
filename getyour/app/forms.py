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
import pendulum

from django import forms
from django.forms.models import ModelForm
from django.contrib.auth.password_validation import validate_password
from formset.upload import FileUploadMixin
from formset.widgets import UploadedFileInput
from formset.collection import FormCollection
from formset.renderers.bootstrap import FormRenderer
from formset.utils import FormMixin

from app.models import (
    HouseholdMembersNew,
    User,
    HouseholdNew,
    AddressRD,
    EligibilityProgram,
    Feedback,
)
from app.constants import rent_own_choices, duration_at_address_choices


class UserForm(ModelForm):
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
class UserUpdateForm(ModelForm):
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


class AddressForm(ModelForm):
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


class DateInput(forms.DateInput):
    input_type = 'date'


class HouseholdForm(ModelForm):
    """ Form for user-defined 'household' data. """
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
        model = HouseholdNew
        fields = (
            'rent_own',
            'duration_at_address',
        )


class HouseholdMembersForm(ModelForm, FileUploadMixin):
    """ Form for user-defined 'individuals in household' data. """
    # Create (hidden) fields to track objects in this form
    id = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)

    class Meta:
        model = HouseholdMembersNew
        fields = (
            'id',
            'full_name',
            'birthdate',
            'identification_path',
        )
        labels = {
            'full_name': "First & Last Name of Individual",
            'birthdate': "Their Birthdate",
            'identification_path': "Upload ID",
        }
        widgets = {
            'birthdate': DateInput(attrs={'type': 'date'}),
            'identification_path': UploadedFileInput,
        }


class HouseholdMembersFormCollection(FormCollection):
    """
    Form Collection to allow users to add/remove 'siblings' to define each
    individuals in their household.
    
    """
    default_renderer = FormRenderer(
        field_css_classes='mb-0',
        collection_css_classes='mb-0 col-12',
    )

    person = HouseholdMembersForm()
    legend = "Tell us about the individuals in your household"
    min_siblings = 1  # minimum number that are required
    # max_siblings = 3  # maximum number the user can submit
    add_label = "Add another person"
    related_field = 'household'
    is_sortable = True

    def retrieve_instance(self, data):
        if data := data.get('person'):
            try:
                return self.instance.members.get(id=data.get('id') or 0)
            except (AttributeError, HouseholdMembersNew.DoesNotExist, ValueError):
                return HouseholdMembersNew(
                    household=self.instance,
                    full_name=data.get('full_name'),
                    birthdate=pendulum.parse(data.get('birthdate')).date(),
                    identification_path=data.get('identification_path'),
                )


class HouseholdFormCollection(FormCollection, FormMixin):
    """
    Form Collection to render the 'household' and 'individuals in household' on
    a single page.
    
    """
    default_renderer = FormRenderer(
        field_css_classes='col-12',
        fieldset_css_classes='col-12',
    )
    household = HouseholdForm()
    members = HouseholdMembersFormCollection()


class AddressLookupForm(forms.Form):
    address = forms.CharField(label='Address')


class FileUploadForm(ModelForm):
    class Meta:
        model = EligibilityProgram
        fields = ['id', 'document_path',]
        widgets = {
            'document_path': forms.ClearableFileInput(attrs={'multiple': True}),
        }


class FeedbackForm(ModelForm):
    feedback_comments = forms.CharField(max_length=500, required=False)
    star_rating = forms.CharField(max_length=1, required=False)

    class Meta:
        model = Feedback
        fields = ['feedback_comments', 'star_rating']
        labels = {
            'star_rating': 'Rating in Stars',
            'feedback_comments': 'Feedback and Comments by Clients',
        }
