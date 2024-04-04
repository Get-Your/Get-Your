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

from app.models import (
    User,
    Household,
    AddressRD,
    EligibilityProgramRD,
    IQProgramRD,
)
from app.backend import get_users_iq_programs


class ProgramChangeForm(forms.Form):

    program_name = forms.ChoiceField(
        label='Select the program to use for this record',
        choices=[(str(x.id), x.friendly_name) for x in EligibilityProgramRD.objects.filter(is_active=True).order_by('friendly_name')],
        widget=forms.Select(),
    )


class ProgramAddForm(forms.Form):
    def __init__(self, user_id, *args, **kwargs):
        # Initialize the form
        super().__init__(*args, **kwargs)

        # Pull user data
        user = User.objects.get(id=user_id)
        household = Household.objects.get(user_id=user.id)
        eligibility_address = AddressRD.objects.filter(
            id=user.address.eligibility_address_id
        ).first()

        # Get all of the IQ Programs for which the user is eligible
        users_iq_programs = get_users_iq_programs(
            user.id,
            household.income_as_fraction_of_ami,
            eligibility_address,
        )
        
        # Return the available IQ Programs the user is not currently applied
        # (IQProgramRD objects are those that the user qualifies for but is not
        # enrolled in). Sort by friendly_name
        self.fields['program_name'].choices = sorted(
            [(str(x.id), x.friendly_name) for x in users_iq_programs if isinstance(x, IQProgramRD)],
            key=lambda x: x[1],
        )

    program_name = forms.ChoiceField(
        label='Select the program to add',
        widget=forms.Select(),
    )