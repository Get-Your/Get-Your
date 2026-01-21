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
from django.core.exceptions import ValidationError
from django.forms.widgets import Textarea
from django.utils.translation import gettext_lazy as _

from app.models import Household
from dashboard.backend import get_iqprogram_requires_fields
from dashboard.backend import get_users_iq_programs
from ref.models import Address as AddressRef
from ref.models import EligibilityProgram as EligibilityProgramRef
from ref.models import IQProgram as IQProgramRef

# Get the user model
User = get_user_model()


class ProgramChangeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        # Return the available Eligibility Programs, sorted by friendly_name
        self.fields["program_name"].choices = list(
            map(
                lambda x: (str(x.id), x.friendly_name),
                EligibilityProgramRef.objects.filter(is_active=True).order_by(
                    "friendly_name",
                ),
            ),
        )

    program_name = forms.ChoiceField(
        label="Select the program to use for this record",
        choices=(),
        widget=forms.Select(),
    )


class IQProgramAddForm(forms.Form):
    def __init__(self, user_id, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        # Pull user data
        user = User.objects.get(id=user_id)
        household = Household.objects.get(user_id=user.id)
        eligibility_address = AddressRef.objects.filter(
            id=user.address.eligibility_address_id,
        ).first()

        # Get all of the IQ Programs for which the user is eligible
        users_iq_programs = get_users_iq_programs(
            user.id,
            household.income_as_fraction_of_ami,
            eligibility_address,
        )

        # Return the available IQ Programs the user is not currently applied
        # (IQProgramRef objects are those that the user qualifies for but is not
        # enrolled in). Sort by friendly_name
        self.fields["program_name"].choices = sorted(
            [
                (str(x.id), x.friendly_name)
                for x in users_iq_programs
                if isinstance(x, IQProgramRef)
            ],
            key=lambda x: x[1],
        )

    program_name = forms.ChoiceField(
        label="Select the program to add",
        widget=forms.Select(),
    )


class EligProgramAddForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        # Return the available Eligibility Programs, sorted by friendly_name
        # Prepend empty (and unusable) option
        self.fields["program_name"].choices = [("", "")] + list(
            map(
                lambda x: (str(x.id), x.friendly_name),
                EligibilityProgramRef.objects.filter(is_active=True).order_by(
                    "friendly_name",
                ),
            ),
        )

    program_name = forms.ChoiceField(
        label="Select the program to add",
        choices=(),
    )

    document_path = forms.FileField(label="Select a file")


class EligibilityProgramRefForm(forms.ModelForm):
    class Meta:
        model = EligibilityProgramRef

        fields = [
            "program_name",
            "ami_threshold",
            "is_active",
            "friendly_name",
            "friendly_description",
        ]

        # Override the widgets for description field
        widgets = {
            "friendly_description": Textarea,
        }


class IQProgramRefForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()

        # Raise a ValidationError on the form if there isn't at least one True
        # `requires_` field
        if not any(cleaned_data.get(x[0]) for x in get_iqprogram_requires_fields()):
            msg = ValidationError(
                _(
                    "At least one 'Requires' box must be checked (otherwise any address anywhere is eligible).",
                ),
                code="invalid",
            )
            for fd, x in get_iqprogram_requires_fields():
                self.add_error(fd, msg)

    class Meta:
        model = IQProgramRef

        req_fields = get_iqprogram_requires_fields()

        program_fields = [
            "program_name",
            "ami_threshold",
            "is_active",
            "enable_autoapply",
            "renewal_interval_year",
        ]
        display_fields = [
            "friendly_name",
            "friendly_category",
            "friendly_description",
            "friendly_supplemental_info",
            "learn_more_link",
            "friendly_eligibility_review_period",
        ]
        address_fields = [x[0] for x in req_fields]

        fields = program_fields + display_fields + address_fields

        # Override the widgets for description field
        widgets = {
            "friendly_description": Textarea,
        }

        # Override the labels for the 'requires_' fields to capitalize the first
        # word and place single quotes around the field name
        labels = {}
        for req, x in req_fields:
            label_list = req.capitalize().split("_")

            # Insert single quotes at the beginning and end of the field name
            label_list[1] = f"'{label_list[1]}"
            label_list[-1] = f"{label_list[-1]}'"

            labels[req] = " ".join(label_list)
