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
from app.models import Address, Household
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
    initial_address_data = []

    address = Address.objects.select_related(
        'eligibility_address',
        'mailing_address'
    ).get(
        user_id=request.user.id
    )

    if address is not None:
        initial_address_data = address.set_initial_form_data()

    household = Household.objects.prefetch_related(
        'members'
    ).get(
        user_id=request.user.id
    )

    user_json_data = {
        "id": request.user.id,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
    }

    if request.method == 'POST':
        # on post, set form to use posted data to fill form in case of error
        user_form = UserForm(request.POST, prefix='user', instance=request.user)
        address_form_set = AddressFormSet(request.POST)
        same_address_form = SameAddressForm(request.POST)
        household_form = HouseholdForm(
            request.POST,
            prefix='household',
            initial={
                'user': request.user.id
            },
            instance=household
        )

        if user_form.is_valid():
            user_form.save()

        if household_form.is_valid():
            household_form.save()

        if address_form_set.is_valid():
            address_info_for_db = []
            for address_form in address_form_set:
                # there will only ever be two address forms total
                # in the set. the first form represents eligibility address
                # and should always have data, but mailing address may be empty
                if address_form.cleaned_data:
                    # create ref_address model
                    new_address = address_form.save()
                    address_info_for_db.append(new_address)

            # create app_address info and then associate 
            # eligibility address and, if needed, mailing address
            if len(address_info_for_db) > 1:
                Address.objects.create(
                    user_id = request.user.id,
                    user_has_updated = False,
                    eligibility_address_id = address_info_for_db[0].id,
                    mailing_address_id = address_info_for_db[1].id,
                )
            else:
                Address.objects.create(
                    user_id = request.user.id,
                    user_has_updated = False,
                    eligibility_address_id = address_info_for_db[0].id,
                    mailing_address_id = address_info_for_db[0].id,
                )

            return render(
                request,
                'dashboard/dashboard.html',
                {
                    "title": "Get FoCo Dashboard",
                },
            )

        # if validation fails, return form with input
        return render(
            request,
            'dashboard/program_form.html',
            {
                'title': 'Program Form',
                'user_form': user_form,
                'address_form_set': address_form_set,
                'same_address_form': same_address_form,
                'household_form': household_form,
                'userJson': user_json_data
            },
        )

    # if not a POST request
    user_form = UserForm(prefix='user', instance=request.user)
    address_form_set = AddressFormSet(initial=initial_address_data)
    same_address_form = SameAddressForm()
    household_form = HouseholdForm(
        prefix='household',
        initial={
            'user': request.user.id
        },
        instance=household
    )

    return render(
            request,
            'dashboard/program_form.html',
            {
                'title': 'Program Form',
                'user_form': user_form,
                'address_form_set': address_form_set,
                'same_address_form': same_address_form,
                'household_form': household_form,
                'userJson': user_json_data
            },
        )
