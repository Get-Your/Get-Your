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

import os
import json
import pendulum
import base64
import logging

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage

from get_your.users.models import User
from ref.models import AddressRef, IQProgramRef
from app.models import HouseholdMembers, IQProgram
from monitor.wrappers import LoggerWrapper

from .forms import UserForm, SameAddressForm, HouseholdForm, AddressFormSet, HouseholdMembersFormSet

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

@login_required()
def dashboard(request, **kwargs):
    user = get_object_or_404(User.objects.prefetch_related(
        'householdmembers',
        'iq_programs',
        'eligibility_files'
    ), pk=request.user.id)

    user_eligibility_record = user.eligibility_files.latest('created_at')
    one_year_ago = pendulum.now().subtract(years=1)

    all_available_programs = IQProgramRef.objects.filter(is_active=True).order_by('friendly_name')
    user_programs_pending_ids = list(user.iq_programs.filter(
        applied_at__isnull=False,
        enrolled_at__isnull=True
    ).values_list(
        'program_id',
        flat=True
    ))

    user_program_ids = list(user.iq_programs.filter(
        enrolled_at__isnull=False
    ).values_list(
        'program_id',flat=True
    ))

    user_program_renewal_ids = list(user.iq_programs.filter(
        enrolled_at__lt=one_year_ago,
        program__renewal_interval_year__isnull=False
    ).values_list(
        'program_id',flat=True
    ))

    all_user_programs = {
        'pending': user_programs_pending_ids,
        'enrolled': user_program_ids,
        'renewals_needed': user_program_renewal_ids
    }

    return render(
        request,
        'dashboard/dashboard.html',
        {
            'user': user,
            'user_eligibility_record': user_eligibility_record,
            'all_available_programs': all_available_programs,
            'all_user_programs': all_user_programs,
            "title": "Get FoCo Dashboard",
        },
    )

@login_required()
def apply_for_program(request):
    data = json.loads(request.body)
    program_id = data.get('programId')
    user_id = request.user.id

    program, created = IQProgram.objects.get_or_create(
        program_id=program_id,
        user_id=user_id,
        defaults={'applied_at': pendulum.now(), 'program_id': program_id, 'user_id': user_id}
    )
    # TODO: add error handling here?
    if created:
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully applied for {program.program.friendly_name}',
            'programId': program_id
        })


@login_required()
def program_form(request, pk, **kwargs):
    user = get_object_or_404(User.objects.prefetch_related('householdmembers'), pk=pk)

    initial_address_queryset = AddressRef.objects.none()

    if user.eligibility_address_id is not None:
        if user.are_addresses_the_same():
            initial_address_queryset = AddressRef.objects.filter(
                id=user.eligibility_address.id
            ).order_by('id')

        else:
            initial_address_queryset = AddressRef.objects.filter(
                id__in=[user.eligibility_address.id, user.mailing_address.id]
            ).order_by('id')

    if request.method == 'POST':
        # on post, set form to use posted data to fill form in case of error
        user_form = UserForm(request.POST, prefix='user', instance=user)
        address_form_set = AddressFormSet(
            request.POST,
            queryset=initial_address_queryset,
            prefix='address'
        )
        same_address_form = SameAddressForm(request.POST)
        household_form = HouseholdForm(
            request.POST,
            prefix='household',
            initial={
                'user': user.id
            },
            instance=user
        )
        householdmembers_form_set = HouseholdMembersFormSet(
            request.POST,
            request.FILES,
            queryset=user.householdmembers.all(),
            prefix='householdmembers'
        )

        if user_form.is_valid():
            user_instance = user_form.save(commit=False)

        if household_form.is_valid():
            household_form.save()

        if address_form_set.is_valid():
            address_info_for_db = []
            for address_form in address_form_set:
                # there will only ever be two address forms total
                # in the set. the first form represents eligibility address
                # and should always have POST data, but mailing address may be empty
                if address_form.cleaned_data:
                    # create ref_address model
                    new_address = address_form.save()
                    address_info_for_db.append(new_address)

            # create app_address info and then associate
            # eligibility address and, if needed, mailing address
            user_instance.eligibility_address = address_info_for_db[0]
            user_instance.mailing_address = address_info_for_db[1] if len(address_info_for_db) > 1 else address_info_for_db[0]
            user_instance.save()

        if householdmembers_form_set.is_valid():
            householdmembers_form_set.save()

            return redirect('dashboard', pk=user.id)

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
                'householdmembers_form_set': householdmembers_form_set,
                'mapsApiKey': os.environ.get('GOOGLE_MAPS_API', '')
            },
        )

    # if not a POST request
    user_form = UserForm(prefix='user', instance=user)
    address_form_set = AddressFormSet(queryset=initial_address_queryset, prefix='address')
    same_address_form = SameAddressForm()
    household_form = HouseholdForm(
        prefix='household',
        initial={
            'user': user.id
        },
        instance=user
    )
    householdmembers_form_set = HouseholdMembersFormSet(
        queryset=user.householdmembers.all(),
        prefix='householdmembers'
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
            'householdmembers_form_set': householdmembers_form_set,
            'mapsApiKey': os.environ.get('GOOGLE_MAPS_API', '')
        },
    )

@login_required()
def view_image(request, pk, image_name, **kwargs):
    householdmember_obj = HouseholdMembers.objects.get(pk=pk)
    file = default_storage.open(image_name)
    blob_data = b''
    for chunk in file.chunks():
        blob_data += chunk

    return render(
        request,
        'dashboard/view_image.html',
        {
            'householdmembers_object': householdmember_obj,
            'blob_data': base64.b64encode(blob_data).decode('utf-8')
        }
    )
