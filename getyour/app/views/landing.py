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
import usaddress
from django.conf import settings as django_settings
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import logout
from app.forms import AddressLookupForm
from app.backend import tag_mapping, address_check, validate_usps
from app.models import IQProgramRD


def index(request):
    if request.method == "POST":
        form = AddressLookupForm(request.POST or None)
        if form.is_valid():
            try:
                # Use usaddress to try to parse the input text into an address

                # Clean the data
                # Remove 'fort collins' - the multi-word city can confuse the
                # parser
                address_str = form.cleaned_data['address'].lower().replace(
                    'fort collins', '')

                raw_address_dict, address_type = usaddress.tag(
                    address_str,
                    tag_mapping,
                )

                # Only continue to validation, etc if a 'Street Address' is
                # found by usaddress
                if address_type != 'Street Address':
                    raise NameError("The address cannot be parsed")

                print(
                    'Address parsing found',
                    raw_address_dict,
                )

                # Help out parsing with educated guesses
                # if 'state' not in raw_address_dict.keys():
                raw_address_dict['state'] = 'CO'
                # if 'city' not in raw_address_dict.keys():
                raw_address_dict['city'] = 'Fort Collins'

                print(
                    'Updated address parsing is',
                    raw_address_dict,
                )

                # Ensure the necessary keys for USPS validation are included
                usps_keys = [
                    'name',
                    'address_1',
                    'address_2',
                    'city',
                    'state',
                    'zipcode']
                raw_address_dict.update(
                    {key: '' for key in usps_keys if key not in raw_address_dict.keys()}
                )

                # Validate to USPS address
                address_dict = validate_usps(raw_address_dict)

                # Check for IQ and Connexion (Internet Service Provider) services
                is_in_gma, has_isp_service = address_check(address_dict)

                if not is_in_gma:
                    return redirect(reverse("app:quick_not_available"))

                if is_in_gma and not has_isp_service:
                    # Connexion status unknown, but since is_in_gma==True, it
                    # will be available at some point
                    request.session['address_dict'] = {
                        'address': address_dict['AddressValidateResponse']['Address']['Address2'],
                        'zipCode': address_dict['AddressValidateResponse']['Address']['Zip5'],
                    }
                    return redirect(reverse("app:quick_coming_soon"))
                else:
                    return redirect(reverse("app:quick_available"))
            except:
                return redirect(reverse("app:quick_not_found"))

    else:
        # Check if the app_status query parameter is present
        # If so, check if it is 'in_progress'
        # If it's in progress, redirect to the app:index page
        if 'app_status' in request.GET:
            if request.GET['app_status'] == 'in_progress':
                # Set the app_status session variable to 'in_progress'
                request.session['app_status'] = 'in_progress'
                return redirect(reverse("app:index"))

        # Check if the user is logged in and has the 'app_status' session var
        # set to 'in_progress'
        in_progress_app_saved = False
        if request.user.is_authenticated and 'app_status' in request.session:
            if request.session['app_status'] == 'in_progress':
                in_progress_app_saved = True

        logout(request)
        return render(
            request,
            'landing/index.html',
            {
                'form': AddressLookupForm(),
                'is_prod': django_settings.IS_PROD,
                'in_progress_app_saved': in_progress_app_saved,
                'iq_programs': IQProgramRD.objects.filter(is_active=True),
            },
        )


def privacy_policy(request):
    # check if user is logged in
    user_logged_in = False
    if request.user.is_authenticated:
        user_logged_in = True

    return render(
        request,
        'landing/privacy_policy.html',
        {
            'is_prod': django_settings.IS_PROD,
            'user_logged_in': user_logged_in,
        },
    )


def programs_info(request):
    return render(
        request,
        'landing/programs_info.html',
        {
            'title': "Programs List",
            'is_prod': django_settings.IS_PROD,
            'iq_programs': IQProgramRD.objects.all(),
        },
    )


def quick_available(request):
    return render(
        request,
        'landing/quick_available.html',
        {
            'title': "Quick Connexion Available",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_not_available(request):
    return render(
        request,
        'landing/quick_not_available.html',
        {
            'title': "Quick Connexion Not Available",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_not_found(request):
    return render(
        request,
        'landing/quick_not_found.html',
        {
            'title': "Quick Connexion Not Found",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_coming_soon(request):
    return render(
        request,
        'landing/quick_coming_soon.html',
        {
            'title': "Quick Connexion Coming Soon",
            'is_prod': django_settings.IS_PROD,
        },
    )