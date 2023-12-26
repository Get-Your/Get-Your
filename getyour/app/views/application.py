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
import usaddress
import magic
import pendulum
import logging
import base64
import io
import re
from urllib.parse import urlencode
import logging

from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict, HttpResponseRedirect, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query_utils import Q
from django.db import IntegrityError
from django.forms.utils import ErrorList
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required

from app.forms import HouseholdForm, UserForm, AddressForm, HouseholdMembersForm, UserUpdateForm, FileUploadForm
from app.backend import form_page_number, tag_mapping, address_check, serialize_household_members, validate_usps, get_in_progress_eligiblity_file_uploads, get_users_iq_programs, what_page, broadcast_email, broadcast_sms, save_renewal_action
from app.models import userfiles_path, AddressRD, Address, EligibilityProgram, Household, IQProgram, User, EligibilityProgramRD
from app.decorators import set_update_mode
from log.wrappers import LoggerWrapper


# Initialize logger
logger = LoggerWrapper(logging.getLogger(__name__))


@login_required(redirect_field_name='auth_next')
def notify_remaining(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='notify_remaining',
            user_id=request.user.id,
        )

        page = what_page(request.user, request)
        return render(
            request,
            "application/notify_remaining.html",
            {
                "next_page": page,
                "title": "Notify Remaining Steps",
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
            function='notify_remaining',
            user_id=user_id,
        )
        raise


def household_definition(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='household_definition',
            user_id=request.user.id,
        )

        return render(
            request,
            "application/household_definition.html",
        )

    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='household_definition',
            user_id=user_id,
        )
        raise

def get_ready(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='get_ready',
            user_id=request.user.id,
        )

        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False
        eligiblity_programs = EligibilityProgramRD.objects.filter(
            is_active=True).order_by('friendly_name')

        # Check if the next query param is set
        # If so, save the renewal action and redirect to the account page
        if request.GET.get('next', False):
            logger.info(
                "Starting renewal process",
                function='get_ready',
                user_id=request.user.id,
            )
            save_renewal_action(request, 'get_ready')
            return redirect('app:account')
        return render(
            request,
            'application/get_ready.html',
            {
                'step': 0,
                'form_page_number': form_page_number,
                'title': "Ready some Necessary Documents",
                'eligiblity_programs': eligiblity_programs,
                'renewal_mode': renewal_mode,
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
            function='get_ready',
            user_id=user_id,
        )
        raise


@set_update_mode
def account(request, **kwargs):

    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = request.session.get(
            'update_mode') if request.session.get('update_mode') else False
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False

        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='account',
                user_id=request.user.id,
            )
            
            try:
                existing = request.user
                if update_mode or renewal_mode or (hasattr(request.user, 'has_viewed_dashboard') and not request.user.has_viewed_dashboard):
                    form = UserUpdateForm(request.POST, instance=existing)
                else:
                    form = UserForm(request.POST, instance=existing)
            except (AttributeError, ObjectDoesNotExist):
                form = UserForm(request.POST or None)

            # Checking the `has_viewed_dashboard` attribute of the user object
            # allows us to determine if the user has already completed the application
            # or if they're returning to update their information from the initial application
            if form.is_valid() and (update_mode or renewal_mode or (hasattr(request.user, 'has_viewed_dashboard') and not request.user.has_viewed_dashboard)):
                instance = form.save(commit=False)

                # Set the attributes to let pre_save know to save history
                instance.update_mode = update_mode
                instance.renewal_mode = renewal_mode
                instance.save()

                if renewal_mode:
                    # Call save_renewal_action after .save() so as not to save
                    # renewal metadata as data updates
                    save_renewal_action(request, 'account')
                    return JsonResponse({"redirect": f"{reverse('app:address')}"})
                elif (hasattr(request.user, 'has_viewed_dashboard') and not request.user.has_viewed_dashboard):
                    return JsonResponse({"redirect": f"{reverse('app:address')}"})
                else:
                    return JsonResponse({"redirect": f"{reverse('app:user_settings')}?page_updated=account"})
            elif form.is_valid():
                passwordCheck = form.passwordCheck()
                passwordCheckDuplicate = form.passwordCheckDuplicate()
                # AJAX data function below, sends data to AJAX function in account.html. If client makes a mistake in password, AJAX lets them know, no page refresh
                # if passwordCheck finds an error like too common a password, no numbers, etc.
                if passwordCheck != None:
                    data = {
                        'result': "error",
                        'message': passwordCheck
                    }
                    return JsonResponse(data)
                # AJAX data function below, sends data to AJAX function in account.html. If client makes a mistake in password, AJAX lets them know, no page refresh
                # Checks if password is the same as the "Enter Password Again" Field
                elif str(passwordCheckDuplicate) != str(form.cleaned_data['password']):
                    data = {
                        'result': "error",
                        'message': passwordCheckDuplicate
                    }
                    return JsonResponse(data)

                try:
                    user = form.save()
                    login(request, user)
                    logger.info(
                        "User account creation successful",
                        function='account',
                        user_id=user.id,
                    )
                    data = {
                        'result': "success",
                    }
                    return JsonResponse(data)
                except AttributeError:
                    logger.warning(
                        f"Login failed. User is: {user}",
                        function='account',
                        user_id=request.user.id,
                    )

                return redirect(reverse("app:address"))

            else:
                # AJAX data function below, sends data to AJAX function in account.html, if clients make a mistake via email or phone number, page lets them know and DOESN'T refresh web page
                # let's them know via AJAX
                error_messages = dict(form.errors.items())

                # Create message_dict by parsing strings or all items of ErrorList,
                # where applicable. Use the prettified field name as each key
                message_dict = {}
                for keyitm in error_messages.keys():
                    val = error_messages[keyitm]

                    # Gather the list of error messages and flatten it
                    message_list = [[y for y in val]
                                    if isinstance(val, ErrorList) else val]
                    flattened_messages = [
                        item for items in message_list for item in items]

                    # Write the messages as a string
                    message_dict.update({
                        keyitm.replace('_', ' ').title(): '. '.join(flattened_messages)
                    })
                # Create error message data by prepending the prettified field name
                # and joining as newlines
                data = {
                    'result': 'error',
                    'message': '\n'.join(
                        [f"{keyitm}: {message_dict[keyitm]}" for keyitm in message_dict.keys()]
                    )
                }
                return JsonResponse(data)
        else:
            logger.debug(
                "Entering function (GET)",
                function='account',
                user_id=request.user.id,
            )
            
            try:
                user = User.objects.get(id=request.user.id)
                form = UserUpdateForm(instance=user)
                update_mode = True
            except Exception:
                form = UserForm()

        return render(
            request,
            'application/account.html',
            {
                'form': form,
                'step': 1,
                'form_page_number': form_page_number,
                'title': "Account",
                'update_mode': update_mode,
                'renewal_mode': renewal_mode,
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
            function='account',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
@set_update_mode
def address(request, **kwargs):

    try:
        if request.session.get('application_addresses'):
            del request.session['application_addresses']

        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = request.session.get(
            'update_mode') if request.session.get('update_mode') else False
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False

        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='address',
                user_id=request.user.id,
            )
            
            addresses = []

            if not update_mode:
                eligibility_address = {
                    'address1': request.POST['address1'],
                    'address2': request.POST['address2'],
                    'city': request.POST['city'],
                    'state': request.POST['state'],
                    'zipcode': request.POST['zip_code'],
                }
                addresses.append(
                    {
                        'address': eligibility_address,
                        'type': 'eligibility',
                        'processed': False
                    })

            # 'no' means the user has a different mailing address
            # compared to their eligibility address
            if request.POST.get('mailing_address') == 'no' or update_mode:

                if request.POST.get('mailing_address') == 'no':
                    logger.info(
                        "Mailing and eligibility addresses are different",
                        function='address',
                        user_id=request.user.id,
                    )

                mailing_address = {
                    'address1': request.POST['mailing_address1'],
                    'address2': request.POST['mailing_address2'],
                    'city': request.POST['mailing_city'],
                    'state': request.POST['mailing_state'],
                    'zipcode': request.POST['mailing_zip_code'],
                }
                addresses.append(
                    {
                        'address': mailing_address,
                        'type': 'mailing',
                        'processed': False
                    })

            request.session['application_addresses'] = json.dumps(
                addresses)
            logger.info(
                f"Sending to address correction: {request.session['application_addresses']}",
                function='address',
                user_id=request.user.id,
            )
            return redirect(reverse("app:address_correction"))
        else:
            logger.debug(
                "Entering function (GET)",
                function='address',
                user_id=request.user.id,
            )

            same_address = True
            if update_mode:
                existing = Address.objects.get(user=request.user)
                mailing_address = AddressRD.objects.get(
                    id=existing.mailing_address_id)
                mailing_address = AddressForm(instance=mailing_address)
                # Will be unused if the user is in update mode
                eligibility_address = AddressForm()
            else:
                try:
                    existing = Address.objects.get(user=request.user)
                    same_address = True if existing.mailing_address_id == existing.eligibility_address_id else False
                    eligibility_address = AddressForm(
                        instance=AddressRD.objects.get(
                            id=existing.eligibility_address_id)
                    )
                    mailing_address = AddressForm(
                        instance=AddressRD.objects.get(
                            id=existing.mailing_address_id)
                    )
                except Address.DoesNotExist:
                    eligibility_address = AddressForm()
                    mailing_address = AddressForm()
            return render(
                request,
                'application/address.html',
                {
                    'eligibility_address_form': eligibility_address,
                    'mailing_address_form': mailing_address,
                    'same_address': same_address,
                    'step': 2,
                    'form_page_number': form_page_number,
                    'title': "Address",
                    'update_mode': update_mode,
                    'renewal_mode': renewal_mode,
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
            function='address',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
def address_correction(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='address_correction',
            user_id=request.user.id,
        )

        try:
            addresses = json.loads(request.session['application_addresses'])
            in_progress_address = [
                address for address in addresses if not address['processed']][0]
            q = QueryDict(urlencode(in_progress_address['address']), mutable=True)
            q_orig = QueryDict(
                urlencode(in_progress_address['address']), mutable=True)

            # Loop through maxLoopIdx+1 times to try different methods of
            # parsing the address
            # Loop 0: as-entered > usaddress > USPS API
            # Loop 1: as-entered with apt/suite keywords replaced with 'unit' >
            # usaddress > USPS API
            # Loop 2: an-entered with keyword replacements > USPS API
            maxLoopIdx = 2
            idx = 0     # starting idx
            flag_needMoreInfo = False   # flag for previous iter needing more info
            while 1:
                logger.info(
                    f"Start loop {idx}",
                    function='address_correction',
                    user_id=request.user.id,
                )

                try:
                    if idx in (0, 1):
                        addressStr = "{ad1} {ad2}, {ct}, {st} {zp}".format(
                            ad1=q['address1'].replace('#', ''),
                            ad2=q['address2'].replace('#', ''),
                            ct=q['city'],
                            st=q['state'],
                            zp=q['zipcode'])

                        try:
                            rawAddressDict, _ = usaddress.tag(
                                addressStr,
                                tag_mapping,
                            )

                        # Go directly to the QueryDict version if there's a usaddress
                        # issue
                        except usaddress.RepeatedLabelError:
                            logger.warning(
                                f"Loop index {idx}; Issue found in usaddress labels - continuing as loop 2",
                                function='address_correction',
                                user_id=request.user.id,
                            )
                            idx = 2
                            raise AttributeError

                        # Ensure the necessary keys for USPS validation are included
                        uspsKeys = [
                            'name',
                            'address_1',
                            'address_2',
                            'city',
                            'state',
                            'zipcode']
                        rawAddressDict.update(
                            {key: '' for key in uspsKeys if key not in rawAddressDict.keys()}
                        )

                    # Validate to USPS address - use usaddress first, then try
                    # with input QueryDict
                    try:
                        if idx == 2:
                            logger.info(
                                f"Loop index {idx}; Attempting USPS validation with input QueryDict: {q}",
                                function='address_correction',
                                user_id=request.user.id,
                            )
                            dict_address = validate_usps(q)
                        else:
                            logger.info(
                                f"Loop index {idx}; Attempting USPS validation with rawAddressDict: {rawAddressDict}",
                                function='address_correction',
                                user_id=request.user.id,
                            )
                            dict_address = validate_usps(rawAddressDict)
                        validationAddress = dict_address['AddressValidateResponse']['Address']
                        logger.info(
                            f"USPS Validation returned {validationAddress}",
                            function='address_correction',
                            user_id=request.user.id,
                        )

                    except KeyError:
                        if idx == maxLoopIdx:
                            if flag_needMoreInfo:
                                raise TypeError(str_needMoreInfo)
                            raise
                        idx += 1
                        raise AttributeError

                    # Ensure 'Address1' is a valid key
                    if 'Address1' not in validationAddress.keys():
                        validationAddress['Address1'] = ''

                    # Kick back to the user if the USPS API needs more information
                    if 'ReturnText' in validationAddress.keys():
                        if idx == maxLoopIdx:
                            logger.info(
                                "Address not found - end of loop",
                                function='address_correction',
                                user_id=request.user.id,
                            )
                            raise TypeError(validationAddress['ReturnText'])

                        # Continue checking, but flag that this was a result from
                        # the USPS API and store the text
                        else:
                            flag_needMoreInfo = True
                            str_needMoreInfo = validationAddress['ReturnText']

                    else:   # success!
                        break

                    if idx == maxLoopIdx:   # this is just here for safety
                        break
                    else:
                        idx += 1
                        raise AttributeError

                except AttributeError:
                    # Use AttributeError to skip to the end of the loop
                    # Note that idx has already been iterated before this point
                    logger.info(
                        f"Loop index {idx}; AttributeError raised to skip to end of loop",
                        function='address_correction',
                        user_id=request.user.id,
                    )
                    if q['address2'] != '':
                        if idx == 1:
                            # For loop 1: if 'ReturnText' is not found and address2 is
                            # not None, remove possible keywords and try again
                            # Note that this will affect later loop iterations
                            logger.info(
                                f"Loop index {idx}; Address not found - try to remove/replace keywords",
                                function='address_correction',
                                user_id=request.user.id,
                            )
                            removeList = ['apt', 'unit', '#']
                            for wrd in removeList:
                                q['address2'] = q['address2'].lower().replace(wrd, '')

                            q['address2'] = 'Unit {}'.format(
                                q['address2'].lstrip())

                    else:
                        # This whole statement updates address2, so if it's blank,
                        # iterate through idx prematurely
                        idx = 2

            # Link to the next page from address_correction.html
            link_next_page = True
            address_feedback = [validationAddress['Address2'],
                                validationAddress['Address1'],
                                validationAddress['City'] + " " + validationAddress['State'] + " " + validationAddress['Zip5']]
            logger.info(
                f"address_feedback is: {address_feedback}",
                function='address_correction',
                user_id=request.user.id,
            )

        except TypeError as msg:
            logger.info(
                "More address information is needed from user",
                function='address_correction',
                user_id=request.user.id,
            )
            # Don't link to the next page from address_correction.html
            link_next_page = False
            # Only pass to the user for the 'more information is needed' case
            # --This is all that has been tested--
            msg = str(msg)
            if 'more information is needed' in msg:
                address_feedback = [
                    msg.replace('Default address: ', ''),
                    "Please press 'back' and re-enter.",
                ]

            else:
                logger.info(
                    "Some other issue than 'more information is needed'",
                    function='address_correction',
                    user_id=request.user.id,
                )
                address_feedback = [
                    "Sorry, we couldn't verify this address through USPS.",
                    "Please press 'back' and re-enter.",
                ]

        except KeyError:
            # Don't link to the next page from address_correction.html
            link_next_page = False
            address_feedback = [
                "Sorry, we couldn't verify this address through USPS.",
                "Please press 'back' and re-enter.",
            ]
            logger.warning(
                "USPS couldn't figure it out!",
                function='address_correction',
                user_id=request.user.id,
            )

        else:
            request.session['usps_address_validate'] = dict_address
            logger.info(
                f"Address match found: {dict_address}",
                function='address_correction',
                user_id=request.user.id,
            )

            # If validation was successful and all address parts are case-insensitive
            # exact matches between entered and validation, skip addressCorrection()

            # Run the QueryDict 'q' to get just dict
            # If just a string input was used (loop idx == 2), use '-' for blanks
            if idx == 2:
                q_orig = {key: q_orig[key] if q[key] !=
                        '' else '-' for key in q_orig.keys()}
            else:
                q_orig = {key: q_orig[key] for key in q_orig.keys()}
            if 'usps_address_validate' in request.session.keys() and \
                dict_address['AddressValidateResponse']['Address']['Address2'].lower() == q_orig['address1'].lower() and \
                    dict_address['AddressValidateResponse']['Address']['Address1'].lower() == q_orig['address2'].lower() and \
            dict_address['AddressValidateResponse']['Address']['City'].lower() == q_orig['city'].lower() and \
            dict_address['AddressValidateResponse']['Address']['State'].lower() == q_orig['state'].lower() and \
                str(dict_address['AddressValidateResponse']['Address']['Zip5']).lower() == q_orig['zipcode'].lower():

                logger.info(
                    "Exact (case-insensitive) address match found",
                    function='address_correction',
                    user_id=request.user.id,
                )
                return redirect(reverse("app:take_usps_address"))

        logger.info(
            "Proceeding to user verification of the matched address",
            function='address_correction',
            user_id=request.user.id,
        )

        return render(
            request,
            'application/address_correction.html',
            {
                'step': 2,
                'form_page_number': form_page_number,
                'link_next_page': link_next_page,
                'address_feedback': address_feedback,
                'address_type': in_progress_address['type'],
                'title': "Address Correction",
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
            function='address_correction',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
def take_usps_address(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='take_usps_address',
            user_id=request.user.id,
        )

        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = request.session.get(
            'update_mode') if request.session.get('update_mode') else False
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False

        try:
            # Use the session var created in addressCorrection(), then remove it
            dict_address = request.session['usps_address_validate']
            del request.session['usps_address_validate']

            # Check for and store GMA and Connexion status
            is_in_gma, has_connexion = address_check(dict_address)

            # Check if an AddressRD object exists by using the
            # dict_address. If the address is not found, create a new one.
            try:
                dict_ref = dict_address['AddressValidateResponse']['Address']
                field_map = [
                    ('Address2', 'address1'),
                    ('Address1', 'address2'),
                    ('City', 'city'),
                    ('State', 'state'),
                    ('Zip5', 'zip_code'),
                ]
                instance = AddressRD.objects.get(
                    address_sha1=AddressRD.hash_address(
                        {key: dict_ref[ref_key] for ref_key, key in field_map})
                )
            except AddressRD.DoesNotExist:
                instance = AddressRD(
                    address1=dict_address['AddressValidateResponse']['Address']['Address2'],
                    address2=dict_address['AddressValidateResponse']['Address']['Address1'],
                    city=dict_address['AddressValidateResponse']['Address']['City'],
                    state=dict_address['AddressValidateResponse']['Address']['State'],
                    zip_code=int(
                        dict_address['AddressValidateResponse']['Address']['Zip5']),
                )
                instance.clean()

            # Record the service area and Connexion status
            instance.is_in_gma = is_in_gma
            instance.is_city_covered = is_in_gma
            instance.has_connexion = has_connexion

            # Final step: mark the address record as 'verified'
            instance.is_verified = True
            instance.save()

            # Get the first address in the list of addresses
            # that is not yet processed
            addresses = json.loads(request.session['application_addresses'])
            address = [
                address for address in addresses if not address['processed']][0]

            # Mark the address as processed and create a new key on the
            # dictionary for storing the instance.
            address['processed'] = True
            address['instance'] = instance.pk

            # Save the updated list of addresses to the session
            request.session['application_addresses'] = json.dumps(addresses)

            # Check if we need to process any other addresses
            if [address for address in addresses if not address['processed']]:
                return redirect(reverse('app:address_correction'))

            # Check to see if a address with the type 'eligibility' exists in the
            # request.session['application_addresses'].
            eligibility_addresses = [
                address for address in addresses if address['type'] == 'eligibility']
            mailing_addresses = [
                address for address in addresses if address['type'] == 'mailing']
            if eligibility_addresses:
                try:
                    # Create and save a record for the user's address using
                    # the Address object
                    if mailing_addresses:
                        Address.objects.create(
                            user=request.user,
                            eligibility_address=AddressRD.objects.get(
                                id=eligibility_addresses[0]['instance']),
                            mailing_address=AddressRD.objects.get(
                                id=mailing_addresses[0]['instance']
                            ),
                        )
                    else:
                        Address.objects.create(
                            user=request.user,
                            eligibility_address=AddressRD.objects.get(
                                id=eligibility_addresses[0]['instance']),
                            mailing_address=AddressRD.objects.get(
                                id=eligibility_addresses[0]['instance']),
                        )
                except IntegrityError:
                    # Update the user's address record if it already exists
                    # (e.g. if the user is updating their address)
                    if mailing_addresses:
                        address = Address.objects.get(user=request.user)
                        address.eligibility_address = AddressRD.objects.get(
                            id=eligibility_addresses[0]['instance']
                        )
                        address.mailing_address = AddressRD.objects.get(
                            id=mailing_addresses[0]['instance']
                        )
                    else:
                        address = Address.objects.get(user=request.user)
                        address.eligibility_address = AddressRD.objects.get(
                            id=eligibility_addresses[0]['instance']
                        )
                        address.mailing_address = AddressRD.objects.get(
                            id=eligibility_addresses[0]['instance']
                        )

                    # Set the attributes to let pre_save know to save history
                    address.update_mode = update_mode
                    address.renewal_mode = renewal_mode

                    address.save()

                if renewal_mode:
                    # Call save_renewal_action after .save() so as not to save
                    # renewal metadata as data updates
                    save_renewal_action(request, 'address')

                return redirect(reverse('app:household'))
            else:
                # We're in update_mode here, so we're only updating the users
                # mailing address. Then redirecting them to their settings page.
                address = Address.objects.get(user=request.user)
                address.mailing_address = AddressRD.objects.get(
                    id=mailing_addresses[0]['instance']
                )

                # Set the attributes to let pre_save know to save history
                address.update_mode = update_mode

                address.save()
                return redirect(f"{reverse('app:user_settings')}?page_updated=address")

        except (KeyError, TypeError):
            logger.warning(
                f"USPS couldn't out the address: {dict_address}",
                function='take_usps_address',
                user_id=request.user.id,
            )
            # HTTP_REFERER sends this button press back to the same page
            # (e.g. removes the button functionality)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except:
            user_id = None
        logger.exception(
            'Uncaught view-level exception',
            function='take_usps_address',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
@set_update_mode
def household(request, **kwargs):

    try:
        if request.session.get('application_addresses'):
            del request.session['application_addresses']

        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = request.session.get(
            'update_mode') if request.session.get('update_mode') else False
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False

        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='household',
                user_id=request.user.id,
            )

            try:
                existing = request.user.household
                form = HouseholdForm(request.POST, instance=existing)
            except (AttributeError, ObjectDoesNotExist):
                form = HouseholdForm(request.POST or None)

            instance = form.save(commit=False)
            instance.user_id = request.user.id

            # Initialize is_income_verified (if first time through the application)
            if not update_mode:
                instance.is_income_verified = False

            # Set the attributes to let pre_save know to save history
            instance.update_mode = update_mode
            instance.renewal_mode = renewal_mode

            instance.save()

            if renewal_mode:
                # Call save_renewal_action after .save() so as not to save
                # renewal metadata as data updates
                save_renewal_action(request, 'household')

            if update_mode:
                return redirect(f'{reverse("app:household_members")}?update_mode=1')
            else:
                return redirect(reverse("app:household_members"))

        else:
            logger.debug(
                "Entering function (GET)",
                function='household',
                user_id=request.user.id,
            )

            try:
                # Query the users table for the user's data
                eligibility = Household.objects.get(
                    user_id=request.user.id)
                form = HouseholdForm(instance=eligibility)
            except Exception:
                form = HouseholdForm()

        return render(
            request,
            'application/household.html',
            {
                'form': form,
                'step': 3,
                'form_page_number': form_page_number,
                'title': "Household",
                'update_mode': update_mode,
                'renewal_mode': renewal_mode,
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
            function='household',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
@set_update_mode
def household_members(request, **kwargs):

    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = request.session.get(
            'update_mode') if request.session.get('update_mode') else False
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False

        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='household_members',
                user_id=request.user.id,
            )

            try:
                existing = request.user.householdmembers

                form = HouseholdMembersForm(
                    request.POST, instance=existing)
            except (AttributeError, ObjectDoesNotExist):
                form = HouseholdMembersForm(request.POST or None)

            file_paths = []
            if form.is_valid():
                instance = form.save(commit=False)

                # fileAmount = 0
                # process is as follows:
                # 1) file is physically saved from the buffer
                # 2) file is then SCANNED using magic
                # 3) file is then deleted or nothing happens if magic sees it's ok

                # update, magic no longer needs to scan from saved file, can now scan from buffer! so with this in mind
                '''
                1) For loop #1 file(s) scanned first
                2) For Loop #2 file saved if file(s) are valid
                '''
                identification_paths = request.POST.getlist('identification_path')
                updated_identification_paths = []

                for _, base64_content in enumerate(identification_paths):
                    # Decode the Base64 string
                    decoded_bytes = base64.b64decode(base64_content)
                    # Create a buffer from the decoded bytes
                    buffer = io.BytesIO(decoded_bytes).getvalue()
                    # fileValidation found below
                    filetype = magic.from_buffer(buffer)

                    # Check if any of the following strings ("PNG", "JPEG", "JPG", "PDF") are in the filetype
                    if any(x in filetype for x in ["PNG", "JPEG", "JPG", "PDF"]):
                        pass
                    else:
                        logger.error(
                            f"File is not a valid file type ({filetype})",
                            function='household_members',
                            user_id=request.user.id,
                        )

                        # Attempt to define household_info to load
                        try:
                            household_info = request.user.householdmembers.household_info
                        except AttributeError:
                            household_info = None

                        return render(
                            request,
                            "application/household_members.html",
                            {
                                'step': 3,
                                "message": "File is not a valid file type. Please upload either  JPG, PNG, OR PDF.",
                                'dependent': str(request.user.household.number_persons_in_household),
                                'list': list(range(request.user.household.number_persons_in_household)),
                                'form': form,
                                'form_page_number': form_page_number,
                                'title': "Household Members",
                                'update_mode': update_mode,
                                'form_data': json.dumps(household_info) if household_info else [],
                            },
                        )

                    # Regular expression pattern for matching PNG, JPEG, JPG, or PDF file extensions
                    pattern = r'(?i)\b(png|jpe?g|pdf)\b'
                    # Search for the pattern in the filetype string
                    match = re.search(pattern, filetype, re.IGNORECASE)
                    # Extract the matched file extension
                    file_extension = match.group(1).lower()
                    file_name = f"household_member_id.{file_extension}"
                    # Assuming file_name is already defined
                    updated_base64_content = base64_content + "," + file_name
                    updated_identification_paths.append(updated_base64_content)

                fileAmount = 0
                for f in updated_identification_paths:
                    file_name = f.split(",")[1]
                    file_contents = f.split(",")[0]
                    content_type = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "pdf": "application/pdf"
                    }.get(file_name.split(".")[1], "text/plain")

                    # Decode the Base64 string
                    decoded_bytes = base64.b64decode(file_contents)

                    # Create a buffer from the decoded bytes
                    buffer = io.BytesIO(decoded_bytes)
                    fileAmount += 1

                    file_path = userfiles_path(
                        request.user,
                        pendulum.now(
                            'utc'
                        ).format(
                            f"YYYY-MM-DD[T]HHmmss[Z_{fileAmount}_{file_name}]"
                        ),
                    )

                    uploaded_file = SimpleUploadedFile(
                        file_name, buffer.read(), content_type)
                    file_paths.append(file_path)
                    default_storage.save(file_path, uploaded_file)

                if fileAmount > 0:
                    logger.info(
                        'Identification file(s) saved successfully',
                        function='household_members',
                        user_id=request.user.id,
                    )
                else:
                    logger.info(
                        'No identification files to upload were found',
                        function=household_members,
                        user_id=request.user.id,
                    )
            else:
                errors = form.errors
                error_message = "The following errors occurred: "
                for field, error_messages in errors.items():
                    for error_message in error_messages:
                        error_message += f"Field: {field} errored because of {error_message}\n"
                return render(
                    request,
                    "application/household_members.html",
                    {
                        'step': 3,
                        "message": error_message,
                        'dependent': str(request.user.household.number_persons_in_household),
                        'list': list(range(request.user.household.number_persons_in_household)),
                        'form': form,
                        'form_page_number': form_page_number,
                        'title': "Household Members",
                        'update_mode': update_mode,
                        'form_data': json.dumps(household_info) if household_info else [],
                    },
                )

            instance.user_id = request.user.id
            instance.household_info = serialize_household_members(
                request, file_paths)

            # Set the attribute to let pre_save know to save history
            instance.update_mode = update_mode
            instance.renewal_mode = renewal_mode

            instance.save()

            if renewal_mode:
                # Call save_renewal_action after .save() so as not to save
                # renewal metadata as data updates
                save_renewal_action(request, 'household_members')

            if update_mode:
                return redirect(f"{reverse('app:user_settings')}?page_updated=household")
            return redirect(reverse("app:programs"))
        
        else:
            logger.debug(
                "Entering function (GET)",
                function='household_members',
                user_id=request.user.id,
            )

            form = HouseholdMembersForm(request.POST or None)
            try:
                household_info = request.user.householdmembers.household_info
            except AttributeError:
                household_info = None

        return render(
            request,
            "application/household_members.html",
            {
                'step': 3,
                'dependent': str(request.user.household.number_persons_in_household),
                'list': list(range(request.user.household.number_persons_in_household)),
                'form': form,
                'form_page_number': form_page_number,
                'title': "Household Members",
                'update_mode': update_mode,
                'form_data': json.dumps(household_info) if household_info else [],
                'renewal_mode': renewal_mode,
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
            function='household_members',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
def programs(request, **kwargs):

    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False
        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='programs',
                user_id=request.user.id,
            )

            # This if/else block essentially does the same thing, but the way we
            # delete programs matters for saving data via our signals.py file.
            # The if block actually triggers the signals.py file to save data
            # while the else block does not.
            if renewal_mode:
                # get the user's eligibility programs
                eligibility_programs = EligibilityProgram.objects.filter(
                    user_id=request.user.id)
                # for every program loop through and delete the program
                for program in eligibility_programs:
                    program.renewal_mode = True
                    program.delete()
            else:
                # In case a user has migrated back to the programs page, clear out their existing
                # eligibility programs and have them start fresh.
                EligibilityProgram.objects.filter(user_id=request.user.id).delete()

            # Serialize POST request
            eligibility_programs = {}
            for key, value in request.POST.items():
                if key == "csrfmiddlewaretoken":
                    continue
                eligibility_programs[key] = value

            # Using the EligibilityProgram model insert multiple rows into the database
            # with the eligibility_programs and the user_id. Each key value in the eligibility_programs is a
            # separate row in the database.
            selected_eligibility_programs = []
            for value in eligibility_programs.values():
                selected_eligibility_programs.append(EligibilityProgram(
                    user_id=request.user.id,
                    program_id=value,
                    renewal_mode=renewal_mode,
                ))

            if renewal_mode:
                save_renewal_action(request, 'eligibility_programs')

            EligibilityProgram.objects.bulk_create(
                selected_eligibility_programs)
            return redirect(reverse("app:files"))
        else:
            logger.debug(
                "Entering function (GET)",
                function='programs',
                user_id=request.user.id,
            )

            # Get all of the programs (except the one with identification and where is_active is False) from the application_EligibilityProgramRD table
            # ordered by the friendly_name field acending
            programs = EligibilityProgramRD.objects.filter(
                is_active=True
            ).order_by(
                'friendly_name'
            )

        return render(
            request,
            'application/programs.html',
            {
                'programs': programs,
                'step': 4,
                'form_page_number': form_page_number,
                'title': "Programs",
                'renewal_mode': renewal_mode,
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
            function='programs',
            user_id=user_id,
        )
        raise

@login_required(redirect_field_name='auth_next')
@set_update_mode
def files(request, **kwargs):
    '''
    Variables:
    fileNames - used to name the files in the database and file upload
    fileAmount - number of file uploads per income verified documentation
    '''

    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        renewal_mode = request.session.get(
            'renewal_mode') if request.session.get('renewal_mode') else False
        users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
            request)

        if request.method == "POST":
            logger.debug(
                "Leaving function (POST)",
                function='files',
                user_id=request.user.id,
            )

            user_file_upload = EligibilityProgram.objects.get(
                pk=request.POST['id'])
            form = FileUploadForm(request.POST, request.FILES,
                                instance=user_file_upload)
            if form.is_valid():
                instance = form.save(commit=False)
                fileNames = []
                fileAmount = 0
                # process is as follows:
                # 1) file is physically saved from the buffer
                # 2) file is then SCANNED using magic
                # 3) file is then deleted or nothing happens if magic sees it's ok

                # update, magic no longer needs to scan from saved file, can now scan from buffer! so with this in mind
                '''
                1) For loop #1 file(s) scanned first
                2) For Loop #2 file saved if file(s) are valid
                '''
                for f in request.FILES.getlist('document_path'):
                    # fileValidation found below
                    filetype = magic.from_buffer(f.read())

                    # Check if any of the following strings ("PNG", "JPEG", "JPG", "PDF") are in the filetype
                    if any(x in filetype for x in ["PNG", "JPEG", "JPG", "PDF"]):
                        pass
                    else:
                        logger.error(
                            f"File is not a valid file type ({filetype})",
                            function='files',
                            user_id=request.user.id,
                        )
                        users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
                            request)
                        return render(
                            request,
                            'application/files.html',
                            {
                                "message": "File is not a valid file type. Please upload either  JPG, PNG, OR PDF.",
                                'form': form,
                                'eligiblity_programs': users_programs_without_uploads,
                                'step': 5,
                                'form_page_number': form_page_number,
                                'title': "Files",
                                'file_upload': json.dumps({'success_status': False}),
                                'renewal_mode': renewal_mode,
                            },
                        )

                for f in request.FILES.getlist('document_path'):
                    fileAmount += 1
                    instance.renewal_mode = renewal_mode

                    # This allows us to save multiple files under the same
                    # Eligibility Program record. Note that the database is updated
                    # each time this loop is run, plus again for the final save()
                    # afterward
                    instance.document_path.save(
                        pendulum.now(
                            'utc'
                        ).format(
                            f"YYYY-MM-DD[T]HHmmss[Z_{fileAmount}_{f}]"
                        ),
                        f,
                    )
                    fileNames.append(str(instance.document_path))
                    logger.debug(
                        f"File {instance.document_path} saved successfully",
                        function='files',
                        user_id=request.user.id,
                    )

                # Save the fileNames list as a single document_path string
                instance.document_path = str(fileNames)
                instance.save()

                if fileAmount > 0:
                    logger.info(
                        'Eligibility Program file(s) saved successfully',
                        function='household_members',
                        user_id=request.user.id,
                    )
                else:
                    logger.info(
                        'No Eligibility Program files to upload were found',
                        function=household_members,
                        user_id=request.user.id,
                    )

                users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
                    request)
                if users_programs_without_uploads.count():
                    return render(
                        request,
                        'application/files.html',
                        {
                            'form': form,
                            'eligiblity_programs': users_programs_without_uploads,
                            'step': 5,
                            'form_page_number': form_page_number,
                            'title': "Files",
                            'file_upload': json.dumps({'success_status': True}),
                            'renewal_mode': renewal_mode,
                        },
                    )
                else:
                    # Get all of the user's eligiblity programs and find the one with the lowest 'ami_threshold' value
                    # which can be found in the related eligiblityprogramrd table
                    lowest_ami = EligibilityProgram.objects.filter(
                        Q(user_id=request.user.id)
                    ).select_related('program').values('program__ami_threshold').order_by('program__ami_threshold').first()

                    # Now save the value of the ami_threshold to the user's household
                    household = Household.objects.get(
                        Q(user_id=request.user.id)
                    )
                    household.income_as_fraction_of_ami = lowest_ami['program__ami_threshold']

                    if renewal_mode:
                        household.is_income_verified = False
                        household.save()

                        # Set the user's last_completed_date to now, as well as set the user's last_renewal_action to null
                        user = User.objects.get(id=request.user.id)
                        user.renewal_mode = True
                        user.last_completed_at = pendulum.now()
                        user.last_renewal_action = None
                        user.save()

                        # Get every IQ program for the user that have a renewal_interval_month
                        # in the IQProgramRD table that is not null
                        users_current_iq_programs = IQProgram.objects.filter(
                            Q(user_id=request.user.id)
                        ).select_related('program').order_by('program__renewal_interval_month').exclude(program__renewal_interval_month__isnull=True)

                        # For every program delete the program if it has a renewal_interval_month
                        # in the IQProgramRD table that is not null
                        for program in users_current_iq_programs:
                            if program.program.renewal_interval_month is not None:
                                program.delete()

                        # Get the user's eligibility address
                        eligibility_address = AddressRD.objects.filter(
                            id=request.user.address.eligibility_address_id).first()

                        # Now get all of the IQ Programs
                        users_iq_programs = get_users_iq_programs(
                            request.user.id, lowest_ami['program__ami_threshold'], eligibility_address)
                        # For every IQ program, check if the user should be automatically enrolled in it if the program
                        # has enable_autoapply set to True and the user's lowest_ami is <= the program's ami_threshold
                        for program in users_iq_programs:
                            if program.enable_autoapply and lowest_ami['program__ami_threshold'] <= program.ami_threshold:
                                # check if the user already has the program in the IQProgram table
                                if not IQProgram.objects.filter(
                                    Q(user_id=request.user.id) & Q(
                                        program_id=program.id)
                                ).exists():
                                    # If the user doesn't have the program in the IQProgram table, then create it
                                    IQProgram.objects.create(
                                        user_id=request.user.id,
                                        program_id=program.id,
                                    )
                            # Check if the current program is in the users_current_iq_programs list
                            if program.id in [program.id for program in users_current_iq_programs] and lowest_ami['program__ami_threshold'] <= program.ami_threshold:
                                # check if the user already has the program in the IQProgram table
                                if not IQProgram.objects.filter(
                                    Q(user_id=request.user.id) & Q(
                                        program_id=program.id)
                                ).exists():
                                    # If the user doesn't have the program in the IQProgram table, then create it
                                    IQProgram.objects.create(
                                        user_id=request.user.id,
                                        program_id=program.id,
                                    )

                        request.session["app_renewed"] = True
                        return redirect(f'{reverse("app:dashboard")}')
                    else:
                        household.save()

                        user = User.objects.get(id=request.user.id)
                        user.last_completed_at = pendulum.now()
                        user.save()

                        # Get the user's eligibility address
                        eligibility_address = AddressRD.objects.filter(
                            id=request.user.address.eligibility_address_id).first()

                        # Now get all of the IQ Programs
                        users_iq_programs = get_users_iq_programs(
                            request.user.id, lowest_ami['program__ami_threshold'], eligibility_address)
                        # For every IQ program, check if the user should be automatically enrolled in it if the program
                        # has enable_autoapply set to True and the user's lowest_ami is <= the program's ami_threshold
                        for program in users_iq_programs:
                            if program.enable_autoapply and lowest_ami['program__ami_threshold'] <= program.ami_threshold:
                                IQProgram.objects.create(
                                    user_id=request.user.id,
                                    program_id=program.id,
                                )
                        return redirect(reverse("app:broadcast"))
        else:
            logger.debug(
                "Entering function (GET)",
                function='files',
                user_id=request.user.id,
            )

            form = FileUploadForm()
            return render(
                request,
                'application/files.html',
                {
                    'form': form,
                    'eligiblity_programs': users_programs_without_uploads,
                    'step': 5,
                    'form_page_number': form_page_number,
                    'title': "Files",
                    'file_upload': json.dumps({'success_status': None}),
                    'renewal_mode': renewal_mode,
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
            function='files',
            user_id=user_id,
        )
        raise


@login_required(redirect_field_name='auth_next')
def broadcast(request, **kwargs):

    try:
        logger.debug(
            "Entering function",
            function='broadcast',
            user_id=request.user.id,
        )

        current_user = request.user
        try:
            broadcast_email(current_user.email)
        except:
            logger.error(
                "There was a problem with sending the email (Sendgrid)",
                function='broadcast',
                user_id=request.user.id,
            )
            # TODO store / save for later: client getting feedback that SendGrid may be down
        phone = str(current_user.phone_number)
        try:
            broadcast_sms(phone)
        except:
            logger.error(
                "Twilio servers may be down",
                function='broadcast',
                user_id=request.user.id,
            )
            # TODO store / save for later: client getting feedback that twilio may be down

        logger.info(
            "Application completed successfully",
            function='broadcast',
            user_id=request.user.id,
        )
        current_user.last_action_notification_at = pendulum.now()

        return render(
            request,
            'application/broadcast.html',
            {
                'program_string': current_user.email,
                'step': 6,
                'form_page_number': form_page_number,
                'title': "Broadcast",
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
            function='broadcast',
            user_id=user_id,
        )
        raise
