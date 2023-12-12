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
import logging 

from django.shortcuts import render, redirect, reverse
from django.contrib.auth import logout

from app.forms import AddressLookupForm
from app.backend import tag_mapping, address_check, validate_usps
from app.models import IQProgramRD
from log.wrappers import LoggerWrapper


# Initialize logger
logger = LoggerWrapper(logging.getLogger(__name__))


def index(request, **kwargs):

    try:
        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='index',
                user_id=request.user.id,
            )
            
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
                        msg = "The address cannot be parsed"
                        logger.error(
                            f"{msg}: {raw_address_dict}",
                            function='index',
                            user_id=request.user.id,
                        )
                        raise NameError(msg)

                    # Help out parsing with educated guesses
                    # if 'state' not in raw_address_dict.keys():
                    raw_address_dict['state'] = 'CO'
                    # if 'city' not in raw_address_dict.keys():
                    raw_address_dict['city'] = 'Fort Collins'

                    logger.info(
                        f"Address form submitted: {raw_address_dict}",
                        function='index',
                        user_id=request.user.id,
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

                        # TODO: This is a quick fix for Connexion availability not
                        # working properly (so we removed Connexion from our
                        # messaging completely). This should be cleaned up and the
                        # templates renamed for clarity.
                        return redirect(reverse("app:quick_available"))

                    else:
                        return redirect(reverse("app:quick_available"))

                except:
                    return redirect(reverse("app:quick_not_found"))

        else:
            logger.debug(
                "Entering function (GET)",
                function='index',
                user_id=request.user.id,
            )

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

            # Logout only if user was previously logged in. logout() apparently
            # resets session vars, so it messes with FirstViewMiddleware if it's
            # run indescriminately
            user_id = request.user.id
            if user_id is not None:
                logout(request)
                logger.info(
                    "User logged out",
                    function='index',
                    user_id=user_id,
                )

            return render(
                request,
                'landing/index.html',
                {
                    'form': AddressLookupForm(),
                    'in_progress_app_saved': in_progress_app_saved,
                    'iq_programs': IQProgramRD.objects.filter(is_active=True),
                },
            )
        
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='index',
            user_id=user_id,
        )
        raise


def privacy_policy(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='privacy_policy',
            user_id=request.user.id,
        )

        # check if user is logged in
        user_logged_in = False
        if request.user.is_authenticated:
            user_logged_in = True

        return render(
            request,
            'landing/privacy_policy.html',
            {
                'user_logged_in': user_logged_in,
            },
        )

    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='privacy_policy',
            user_id=user_id,
        )
        raise


def programs_info(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='programs_info',
            user_id=request.user.id,
        )

        return render(
            request,
            'landing/programs_info.html',
            {
                'title': "Programs List",
                'iq_programs': IQProgramRD.objects.all(),
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='programs_info',
            user_id=user_id,
        )
        raise


def quick_available(request, **kwargs):
    
    try:
        logger.debug(
            "Entering function",
            function='quick_available',
            user_id=request.user.id,
        )

        return render(
            request,
            'landing/quick_available.html',
            {
                'title': "Quick Connexion Available",
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='quick_available',
            user_id=user_id,
        )
        raise


def quick_not_available(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='quick_not_available',
            user_id=request.user.id,
        )

        return render(
            request,
            'landing/quick_not_available.html',
            {
                'title': "Quick Connexion Not Available",
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='quick_not_available',
            user_id=user_id,
        )
        raise


def quick_not_found(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='quick_not_found',
            user_id=request.user.id,
        )

        return render(
            request,
            'landing/quick_not_found.html',
            {
                'title': "Quick Connexion Not Found",
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='quick_not_found',
            user_id=user_id,
        )
        raise


def quick_coming_soon(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='quick_coming_soon',
            user_id=request.user.id,
        )

        return render(
            request,
            'landing/quick_coming_soon.html',
            {
                'title': "Quick Connexion Coming Soon",
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='quick_coming_soon',
            user_id=user_id,
        )
        raise
