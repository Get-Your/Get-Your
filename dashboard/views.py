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

import json
import logging

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from .forms import UserForm, AddressForm, HouseholdForm, EligibilityForm

from monitor.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

@login_required(redirect_field_name='auth_next')
def dashboard(request, **kwargs):
    return render(
            request,
            'dashboard/dashboard.html',
            {
                "title": "Get FoCo Dashboard",
            },
        )

@login_required(redirect_field_name='auth_next')
def program_form(request, **kwargs):
    user_form = UserForm(prefix='user')
    address_form = AddressForm(prefix='home_address')
    household_form = HouseholdForm(prefix='household')
    json_data = {
        "id": request.user.id,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
    }

    return render(
            request,
            'dashboard/program_form.html',
            {
                'title': 'Program Form',
                'user_form': user_form,
                'address_form': address_form,
                'household_form': household_form,
                'userJson': json_data
            },
        )

@login_required(redirect_field_name='auth_next')
def eligibility_form(request, **kwargs):
    eligibility_form = EligibilityForm(prefix='user')

    return render(
        request,
        'dashboard/eligibility_form.html',
        {
            'title': 'Program Form',
            'eligibility_form': eligibility_form,
        }
    )
