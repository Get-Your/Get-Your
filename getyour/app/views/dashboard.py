"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2023

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
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, reverse
from app.forms import FeedbackForm
from app.backend import address_check, get_users_iq_programs
from app.models import AddressRD, IQProgram, IQProgramRD


def dashboard(request):
    request.session['update_mode'] = False
    qualified_programs = 0
    active_programs = 0
    pending_programs = 0

    # Get the user's eligibility address
    eligibility_address = AddressRD.objects.filter(
        id=request.user.address.eligibility_address_id).first()
    users_iq_programs = get_users_iq_programs(
        request.user.id, request.user.household.income_as_fraction_of_ami, eligibility_address)
    for program in users_iq_programs:
        # If the program's visibility is 'block' or the status is `ACTIVE` or `PENDING`, it means the user is eligible for the program
        # so we'll count it for their total number of programs they qualify for
        if program.status_for_user == 'ACTIVE' or program.status_for_user == 'PENDING' or program.status_for_user == '':
            qualified_programs += 1

        # If a program's status_for_user is 'PENDING' add 1 to the pending number and subtract 1 from the qualified_programs
        if program.status_for_user == 'PENDING':
            pending_programs += 1
            qualified_programs -= 1
        # If a program's status_for_user is 'ACTIVE' add 1 to the active number and subtract 1 from the qualified_programs
        elif program.status_for_user == 'ACTIVE':
            active_programs += 1
            qualified_programs -= 1

    # By default we assume the user has viewed the dashboard, but if they haven't
    # we set the proxy_viewed_dashboard flag to false and update the user
    # in the database to say that they have viewed the dashboard. This obviates
    # the need to create some AJAX call to a Django template to update the database
    # when the user views the dashboard.
    proxy_viewed_dashboard = True
    if request.user.has_viewed_dashboard == False:
        proxy_viewed_dashboard = False
        request.user.has_viewed_dashboard = True
        request.user.save()

    return render(
        request,
        'dashboard/dashboard.html',
        {
            "title": "Get FoCo Dashboard",
            "dashboard_color": "var(--yellow)",
            "program_list_color": "white",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            "iq_programs": users_iq_programs,
            "qualified_programs": qualified_programs,
            "pending_programs": pending_programs,
            "active_programs": active_programs,
            "clientName": request.user.first_name,
            "clientEmail": request.user.email,
            'proxy_viewed_dashboard': proxy_viewed_dashboard,
            'badge_visible': request.user.household.is_income_verified,
        },
    )


def quick_apply(request, iq_program):
    in_gma_with_no_service = False

    # Get the IQProgramRD object for the iq_program
    iq_program = IQProgramRD.objects.get(
        program_name=iq_program)
    
    # Get the user's get_users_iq_programs and check if 
    # the IQProgramRD object is in the list. If it is not,
    # throw a 500 error, else continue
    eligibility_address = AddressRD.objects.filter(
        id=request.user.address.eligibility_address_id).first()
    users_iq_programs = get_users_iq_programs(
        request.user.id, request.user.household.income_as_fraction_of_ami, eligibility_address)
    if iq_program not in users_iq_programs:
        raise Exception(f"User is not eligible for {iq_program.program_name}.")
    
    # Check if the user and program already exist in the IQProgram table
    # If they do not, create a new IQProgram object
    if not IQProgram.objects.filter(user_id=request.user.id, program_id=iq_program.id).exists():
        # Create and save a new IQProgram object with the user_id and program_id
        IQProgram.objects.create(
            user_id=request.user.id, program_id=iq_program.id)

    if iq_program.program_name == 'connexion':
        # Get the user's address from the AddressRD table by joining the eligibility_address_id
        # to the AddressRD table's id
        addr = AddressRD.objects.get(
            id=request.user.address.eligibility_address_id)
        # Check for Connexion services
        # Recreate the relevant parts of addressDict as if from validate_usps()
        address_dict = {
            'AddressValidateResponse': {
                'Address': {
                    'Address2': addr.address1,
                    'Zip5': addr.zip_code,
                },
            },
        }
        is_in_gma, has_isp_service = address_check(address_dict)
        # Connexion (Internet Service Provider) status unknown, but since isInGMA==True at this point in
        # the application, Connexion will be available at some point
        if is_in_gma and not has_isp_service:    # this covers both None and False
            in_gma_with_no_service = True

    return render(
        request,
        "dashboard/quick_apply.html",
        {
            'program_name': iq_program.program_name.title(),
            'title': f"{iq_program.program_name.title()} Application Complete",
            'in_gma_with_no_service': in_gma_with_no_service,
        },
    )


def user_settings(request):
    request.session['update_mode'] = False
    # Get the success query string parameter
    page_updated = request.GET.get('page_updated')
    if page_updated:
        request.session['page_updated'] = page_updated
        return redirect(reverse('app:user_settings'))

    if 'page_updated' in request.session:
        page_updated = request.session.get('page_updated')
        del request.session['page_updated']
    else:
        page_updated = None

    return render(
        request,
        'dashboard/user_settings.html',
        {
            "dashboard_color": "white",
            "program_list_color": "white",
            "Settings_color": "var(--yellow)",
            "Privacy_Policy_color": "white",
            "name": request.user.first_name,
            "lastName": request.user.last_name,
            "email": request.user.email,
            "routes": {
                "account": reverse('app:account'),
                "address": reverse('app:address'),
                "household": reverse('app:household'),
            },
            "page_updated": json.dumps({'page_updated': page_updated}, cls=DjangoJSONEncoder),
        },
    )


def privacy(request):
    return render(
        request,
        'dashboard/privacy.html',
        {
            "dashboard_color": "white",
            "program_list_color": "white",
            "Settings_color": "white",
            "Privacy_Policy_color": "var(--yellow)",
        },
    )


def qualified_programs(request):
    # Get the user's eligibility address
    eligibility_address = AddressRD.objects.filter(
        id=request.user.address.eligibility_address_id).first()
    users_iq_programs = get_users_iq_programs(
        request.user.id, request.user.household.income_as_fraction_of_ami, eligibility_address)

    order_by = request.GET.get('order_by')
    if order_by and order_by == 'eligible':
        users_iq_programs = sorted(users_iq_programs, key=lambda x: (
            x.status_for_user, x.status_for_user))
    elif order_by:
        users_iq_programs = sorted(users_iq_programs, key=lambda x: (
            x.status_for_user.lower() != order_by, x.status_for_user))

    return render(
        request,
        'dashboard/qualified_programs.html',
        {
            "title": "Qualified Programs",
            "dashboard_color": "white",
            "program_list_color": "var(--yellow)",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            "iq_programs": users_iq_programs,
        },
    )


def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("app:feedback_received"))


def feedback_received(request):
    return render(
        request,
        "dashboard/feedback_received.html",
        {
            'title': "Feedback Received",
        },
    )


def programs_list(request):
    # Get the user's eligibility address
    eligibility_address = AddressRD.objects.filter(
        id=request.user.address.eligibility_address_id).first()
    users_iq_programs = get_users_iq_programs(
        request.user.id, request.user.household.income_as_fraction_of_ami, eligibility_address)
    return render(
        request,
        'dashboard/programs_list.html',
        {
            "page_title": "Programs List",
            "dashboard_color": "white",
            "program_list_color": "var(--yellow)",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            'title': "Programs List",
            'iq_programs': users_iq_programs,
        },
    )