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
from django.contrib.auth.password_validation import validate_password

# Get the user model
User = get_user_model()


class UserForm(forms.ModelForm):
    password2 = forms.CharField(
        label="Enter Password Again",
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
        ]  # password between email and phone number
        labels = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "password": "Password",
            "email": "Email",
            "phone_number": "Phone Number",
        }

    def passwordCheck(self):
        password = self.cleaned_data["password"]
        try:
            validate_password(password, user=None, password_validators=None)
        except Exception as e:
            return str(e)

    def passwordCheckDuplicate(self):
        cd = self.cleaned_data
        if cd["password"] != cd["password2"]:
            return "Passwords don't match."
        return cd["password"]

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
        fields = ["first_name", "last_name", "email", "phone_number"]
        labels = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "phone_number": "Phone Number",
        }

    # Save function that will update the user's
    # first name, last name, email, and phone number
    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit=False)
        if commit:
            user.save()
        return user
