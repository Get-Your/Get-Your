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
from django.core.exceptions import ValidationError

from .forms import UserForm, AddressFormSet, HouseholdForm, SameAddressForm
from get_your.users.models import User
from app.models import Address
from app.backend.address import validate_usps
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
    user_with_relationships = User.objects.select_related(
        'address',
        'household'
    ).get(
        pk=request.user.id
    )

    json_data = {
        "id": request.user.id,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
    }

    if request.method == 'POST':
        user_form = UserForm(request.POST, prefix='user', instance=user_with_relationships)
        address_form_set = AddressFormSet(request.POST)
        household_form = HouseholdForm(request.POST, prefix='household')
        same_address_form = SameAddressForm(request.POST)
        
        if user_form.is_valid():
            # user_form.save()
            print('user valid')

        if household_form.is_valid():
            # household_form.save()
            print('household valid')

        if address_form_set.is_valid():
            # TODO: figure out what to do when forms are valid
            address_info_for_db = []
            for address_form in address_form_set:
                # there will only ever be two address forms total
                # in the set. the first form represents eligibility address
                # and should always have data, but mailing address may be empty
                if address_form.cleaned_data:
                    # USPS is checked automatically
                    address_info_for_db.append(address_form.cleaned_data)

            # need to create address info and then associate 
            # eligibility address and, if needed, mailing address

        else:
            return render(
            request,
            'dashboard/program_form.html',
            {
                'title': 'Program Form',
                'user_form': user_form,
                'address_form_set': address_form_set,
                'same_address_form': same_address_form,
                'household_form': household_form,
                'userJson': json_data
            },
        )

    user_form = UserForm(prefix='user', instance=user_with_relationships)
    address_form_set = AddressFormSet()
    same_address_form = SameAddressForm()
    household_form = HouseholdForm(prefix='household')

    return render(
            request,
            'dashboard/program_form.html',
            {
                'title': 'Program Form',
                'user_form': user_form,
                'address_form_set': address_form_set,
                'same_address_form': same_address_form,
                'household_form': household_form,
                'userJson': json_data
            },
        )
