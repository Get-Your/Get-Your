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
import datetime
import logging
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings as django_settings
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, logout, get_user_model, authenticate
from django.http import QueryDict, HttpResponse, HttpResponseRedirect, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import BadHeaderError
from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from app.forms import HouseholdForm, HouseholdUpdateForm, UserForm, AddressForm, AddressLookupForm, FutureEmailForm, HouseholdMembersForm, UserUpdateForm, FileUploadForm, FeedbackForm
from app.backend import address_check, serialize_household_members, validate_usps, enroll_connexion_updates, model_to_dict, authenticate, get_in_progress_eligiblity_file_uploads, get_users_iq_programs, what_page, blob_storage_upload, broadcast_email, broadcast_sms, broadcast_email_pw_reset
from app.models import AddressRD, Address, EligibilityProgram, Household, IQProgram, User, IQProgramRD, EligibilityProgramRD
from app.decorators import set_update_mode
from app.qualification_status import QualificationStatus


form_page_number = 6


# Use the following tag mapping for USPS standards for all functions
tag_mapping = {
    'Recipient': 'recipient',
    'AddressNumber': 'address_2',
    'AddressNumberPrefix': 'address_2',
    'AddressNumberSuffix': 'address_2',
    'StreetName': 'address_2',
    'StreetNamePreDirectional': 'address_2',
    'StreetNamePreModifier': 'address_2',
    'StreetNamePreType': 'address_2',
    'StreetNamePostDirectional': 'address_2',
    'StreetNamePostModifier': 'address_2',
    'StreetNamePostType': 'address_2',
    'CornerOf': 'address_2',
    'IntersectionSeparator': 'address_2',
    'LandmarkName': 'address_2',
    'USPSBoxGroupID': 'address_2',
    'USPSBoxGroupType': 'address_2',
    'USPSBoxID': 'address_2',
    'USPSBoxType': 'address_2',
    'BuildingName': 'address_1',
    'OccupancyType': 'address_1',
    'OccupancyIdentifier': 'address_1',
    'SubaddressIdentifier': 'address_1',
    'SubaddressType': 'address_1',
    'PlaceName': 'city',
    'StateName': 'state',
    'ZipCode': 'zipcode',
}


def index(request):
    if request.method == "POST":
        form = AddressLookupForm(request.POST or None)
        if form.is_valid():
            try:
                form.save()

                # Use usaddress to try to parse the input text into an address

                # Clean the data
                # Remove 'fort collins' - the multi-word city can confuse the
                # parser
                addressStr = form.cleaned_data['address'].lower().replace(
                    'fort collins', '')

                rawAddressDict, addressType = usaddress.tag(
                    addressStr,
                    tag_mapping,
                )

                # Only continue to validation, etc if a 'Street Address' is
                # found by usaddress
                if addressType != 'Street Address':
                    raise NameError("The address cannot be parsed")

                print(
                    'Address parsing found',
                    rawAddressDict,
                )

                # Help out parsing with educated guesses
                # if 'state' not in rawAddressDict.keys():
                rawAddressDict['state'] = 'CO'
                # if 'city' not in rawAddressDict.keys():
                rawAddressDict['city'] = 'Fort Collins'

                print(
                    'Updated address parsing is',
                    rawAddressDict,
                )

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

                # Validate to USPS address
                addressDict = validate_usps(rawAddressDict)

                # Check for IQ and Connexion services
                isInGMA, hasConnexion = address_check(addressDict)

                if isInGMA:
                    # Connexion status unknown, but since isInGMA==True, it
                    # will be available at some point
                    if not hasConnexion:    # this covers both None and False
                        # Write a dictionary to the session var with 'address'
                        # and 'zipCode' for use when quick-applying for Connexion
                        request.session['address_dict'] = {
                            'address': addressDict['AddressValidateResponse']['Address']['Address2'],
                            'zipCode': addressDict['AddressValidateResponse']['Address']['Zip5'],
                        }
                        return redirect(reverse("app:quick_coming_soon"))

                    else:  # hasConnexion==True is the only remaining option
                        return redirect(reverse("app:quick_available"))

                else:
                    return redirect(reverse("app:quick_not_available"))

            except:
                # TODO implement look into logs!
                logging.warning("insert valid zipcode")
                return (redirect(reverse("app:quick_not_found")))

    else:
        # Check if the app_status query parameter is present
        # If so, check if it is 'in_progress'
        # If it's in progress, redirect to the app:index page
        if 'app_status' in request.GET:
            if request.GET['app_status'] == 'in_progress':
                # Set the app_status session variable to 'in_progress'
                request.session['app_status'] = 'in_progress'
                return redirect(reverse("app:index"))

        form = AddressLookupForm()

        # Check if the user is logged in and has the 'app_status' session var
        # set to 'in_progress'
        in_progress_app_saved = False
        if request.user.is_authenticated and 'app_status' in request.session:
            if request.session['app_status'] == 'in_progress':
                in_progress_app_saved = True

        logout(request)
        return render(
            request,
            'index.html',
            {
                'form': form,
                'is_prod': django_settings.IS_PROD,
                'in_progress_app_saved': in_progress_app_saved,
                'iq_programs': IQProgramRD.objects.filter(is_active=True),
            },
        )


def get_ready(request):
    eligiblity_programs = EligibilityProgramRD.objects.filter(
        is_active=True).order_by('friendly_name')
    return render(
        request,
        'get_ready.html',
        {
            'step': 0,
            'form_page_number': form_page_number,
            'title': "Ready some Necessary Documents",
            'is_prod': django_settings.IS_PROD,
            'eligiblity_programs': eligiblity_programs,
        },
    )


@set_update_mode
def account(request):
    if request.method == "POST":
        # Check if the update_mode exists in the POST data.
        update_mode = request.POST.get('update_mode')
        try:
            existing = request.user
            if update_mode:
                form = UserUpdateForm(request.POST, instance=existing)
            else:
                form = UserForm(request.POST, instance=existing)
        except AttributeError or ObjectDoesNotExist:
            form = UserForm(request.POST or None)

        if form.is_valid() and update_mode:
            form.save()
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
                print("userloggedin")
                data = {
                    'result': "success",
                }
                return JsonResponse(data)
            except AttributeError:
                print("user error, login not saved, user is: " + str(user))

            return redirect(reverse("app:address"))

        else:
            # AJAX data function below, sends data to AJAX function in account.html, if clients make a mistake via email or phone number, page lets them know and DOESN'T refresh web page
            # let's them know via AJAX
            errorMessages = dict(form.errors.items())
            if "email" in errorMessages:
                data = {
                    'result': "error",
                    'message': errorMessages["email"]
                }
            elif "phone_number" in errorMessages:
                data = {
                    'result': "error",
                    'message':  errorMessages["phone_number"]
                }
            return JsonResponse(data)
    else:
        if request.session.get('update_mode'):
            # Query the users table for the user's data
            user = User.objects.get(id=request.user.id)
            form = UserUpdateForm(instance=user)
        else:
            form = UserForm()

    return render(
        request,
        'account.html',
        {
            'form': form,
            'step': 1,
            'form_page_number': form_page_number,
            'title': "Account",
            'is_prod': django_settings.IS_PROD,
            'update_mode': request.session.get('update_mode'),
        },
    )


def address(request):
    if request.method == "POST":
        instance = AddressRD(
            address1=request.POST['address1'],
            address2=request.POST['address2'],
            city=request.POST['city'],
            state=request.POST['state'],
            zip_code=request.POST['zip_code'],
        )
        request.session['in_progress_address'] = json.dumps(
            model_to_dict(instance), cls=DjangoJSONEncoder)
        return redirect(reverse("app:address_correction"))
    else:
        form = AddressForm()
        return render(
            request,
            'address.html',
            {
                'form': form,
                'step': 2,
                'request.user': request.user,
                'form_page_number': form_page_number,
                'title': "Address",
                'is_prod': django_settings.IS_PROD,
            },
        )


def address_correction(request):
    try:
        address = json.loads(request.session['in_progress_address'])
        q = QueryDict('', mutable=True)
        q.update({"address": address['address1'],
                  "address2": address['address2'],
                  "city": address['city'],
                  "state": address['state'],
                  "zipcode": str(address['zip_code']), })

        q_orig = QueryDict('', mutable=True)
        q_orig.update({"address": address['address1'],
                       "address2": address['address2'],
                       "city": address['city'],
                       "state": address['state'],
                       "zipcode": str(address['zip_code']), })

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
            print("Start loop {}".format(idx))

            try:
                if idx in (0, 1):
                    addressStr = "{ad1} {ad2}, {ct}, {st} {zp}".format(
                        ad1=q['address'].replace('#', ''),
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
                        print('Error in usaddress labels - continuing as loop 2')
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
                        print('Input QueryDict:', q)
                        dict_address = validate_usps(q)
                    else:
                        print('rawAddressDict:', rawAddressDict)
                        dict_address = validate_usps(rawAddressDict)
                    validationAddress = dict_address['AddressValidateResponse']['Address']
                    print('USPS Validation return:', validationAddress)

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
                        print('Address not found - end of loop')
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
                print('AttributeError raised with idx', idx)
                if q['address2'] != '':
                    if idx == 1:
                        # For loop 1: if 'ReturnText' is not found and address2 is
                        # not None, remove possible keywords and try again
                        # Note that this will affect later loop iterations
                        print('Address not found - try to remove/replace keywords')
                        removeList = ['apt', 'unit', '#']
                        for wrd in removeList:
                            q['address2'] = q['address2'].lower().replace(wrd, '')

                        q['address2'] = 'Unit {}'.format(
                            q['address2'].lstrip())

                else:
                    # This whole statement updates address2, so if it's blank,
                    # iterate through idx prematurely
                    idx = 2

        program_string_2 = [validationAddress['Address2'],
                            validationAddress['Address1'],
                            validationAddress['City'] + " " + validationAddress['State'] + " " + str(validationAddress['Zip5'])]
        print('program_string_2', program_string_2)

    except TypeError as msg:
        print("More address information is needed from user")
        # Only pass to the user for the 'more information is needed' case
        # --This is all that has been tested--
        msg = str(msg)
        if 'more information is needed' in msg:
            program_string_2 = [
                msg.replace('Default address: ', ''),
                "Please press 'back' and re-enter.",
            ]

        else:
            print("Some other issue than 'more information is needed'")
            program_string_2 = [
                "Sorry, we couldn't verify this address through USPS.",
                "Please press 'back' and re-enter.",
            ]

    except KeyError:
        program_string_2 = [
            "Sorry, we couldn't verify this address through USPS.",
            "Please press 'back' and re-enter.",
        ]
        print("USPS couldn't figure it out!")

    else:
        request.session['usps_address_validate'] = dict_address
        print(q)
        print(dict_address)

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
            dict_address['AddressValidateResponse']['Address']['Address2'].lower() == q_orig['address'].lower() and \
                dict_address['AddressValidateResponse']['Address']['Address1'].lower() == q_orig['address2'].lower() and \
            dict_address['AddressValidateResponse']['Address']['City'].lower() == q_orig['city'].lower() and \
            dict_address['AddressValidateResponse']['Address']['State'].lower() == q_orig['state'].lower() and \
        str(dict_address['AddressValidateResponse']['Address']['Zip5']).lower() == q_orig['zipcode'].lower():

            print('Exact (case-insensitive) address match!')
            return redirect(reverse("app:take_usps_address"))

    print('Address match not found - proceeding to addressCorrection')
    program_string = [address['address1'], address['address2'],
                      address['city'] + " " + address['state'] + " " + str(address['zip_code'])]
    return render(
        request,
        'address_correction.html',
        {
            'step': 2,
            'form_page_number': form_page_number,
            'program_string': program_string,
            'program_string_2': program_string_2,
            'title': "Address Correction",
            'is_prod': django_settings.IS_PROD,
        },
    )


def take_usps_address(request):
    try:
        # Use the session var created in addressCorrection(), then remove it
        dict_address = request.session['usps_address_validate']
        del request.session['usps_address_validate']

        # Check for and store GMA and Connexion status
        is_in_gma, has_connexion = address_check(dict_address)

        # Check if an addressnew_rearch object exists by using the
        # dict_address. If the address is not found, create a new one.
        try:
            instance = AddressRD.objects.get(
                address1=dict_address['AddressValidateResponse']['Address']['Address2'],
                address2=dict_address['AddressValidateResponse']['Address']['Address1'],
                city=dict_address['AddressValidateResponse']['Address']['City'],
                state=dict_address['AddressValidateResponse']['Address']['State'],
                zip_code=dict_address['AddressValidateResponse']['Address']['Zip5'],
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

        # Record the service area and Connexion status
        instance.is_in_gma = is_in_gma
        instance.is_city_covered = is_in_gma
        instance.has_connexion = has_connexion

        # Final step: mark the address record as 'verified'
        instance.is_verified = True
        instance.save()

        if is_in_gma:
            # Create and save a record for the user's address using
            # the Address object
            Address.objects.create(
                user=request.user,
                eligibility_address=instance,
                mailing_address=instance,
            )
            return redirect(reverse("app:household"))
        else:
            return redirect(reverse("app:not_available"))
    except KeyError or TypeError:
        print("USPS couldn't figure it out!")
        # HTTP_REFERER sends this button press back to the same page
        # (e.g. removes the button functionality)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@set_update_mode
def household(request):
    if request.method == "POST":
        # Check if the update_mode exists in the POST data.
        update_mode = request.POST.get('update_mode')
        try:
            existing = request.user.eligibility
            form = HouseholdForm(request.POST, instance=existing)
        except AttributeError or ObjectDoesNotExist:
            form = HouseholdForm(request.POST or None)

        instance = form.save(commit=False)
        instance.user_id = request.user.id
        instance.is_income_verified = False
        instance.save()
        if update_mode:
            return redirect(f'{reverse("app:household_members")}?update_mode=1')
        else:
            return redirect(reverse("app:household_members"))

    else:
        if request.session.get('update_mode'):
            # Query the users table for the user's data
            eligibility = Household.objects.get(
                user_id=request.user.id)
            form = HouseholdUpdateForm(instance=eligibility)
        else:
            form = HouseholdForm()

    return render(
        request,
        'household.html',
        {
            'form': form,
            'step': 3,
            'form_page_number': form_page_number,
            'title': "Household",
            'is_prod': django_settings.IS_PROD,
            'update_mode': request.POST.get('update_mode'),
        },
    )


@set_update_mode
def household_members(request):
    if request.method == "POST":
        # Check if the update_mode exists in the POST data.
        update_mode = request.POST.get('update_mode')
        try:
            existing = request.user.householdmembers
            form = HouseholdMembersForm(request.POST, instance=existing)
        except AttributeError or ObjectDoesNotExist:
            form = HouseholdMembersForm(request.POST or None)

        instance = form.save(commit=False)
        instance.user_id = request.user.id
        instance.household_info = serialize_household_members(request)
        instance.save()
        if update_mode:
            return redirect(f"{reverse('app:user_settings')}?page_updated=financial")
        return redirect(reverse("app:programs"))
    else:
        form = HouseholdMembersForm(request.POST or None)
        try:
            household_info = request.user.householdmembers.household_info
        except AttributeError:
            household_info = None

    return render(
        request,
        "household_members.html",
        {
            'step': 3,
            'dependent': str(request.user.household.number_persons_in_household),
            'list': list(range(request.user.household.number_persons_in_household)),
            'form': form,
            'form_page_number': form_page_number,
            'title': "Household Members",
            'is_prod': django_settings.IS_PROD,
            'update_mode': request.session.get('update_mode'),
            'form_data': json.dumps(household_info) if household_info else [],
        },
    )


def quick_apply(request, iq_program):
    # Get the IQProgramRD object for the iq_program
    iq_program = IQProgramRD.objects.get(
        program_name=iq_program)

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
        addressDict = {
            'AddressValidateResponse': {
                'Address': {
                    'Address2': addr.address1,
                    'Zip5': addr.zip_code,
                },
            },
        }
        _, has_connexion = address_check(addressDict)
        # Connexion status unknown, but since isInGMA==True at this point in
        # the application, Connexion will be available at some point
        if not has_connexion:    # this covers both None and False
            return redirect(reverse("app:coming_soon"))

    return render(
        request,
        "quick_apply.html",
        {
            'programName': iq_program.program_name.title(),
            'title': f"{iq_program.program_name.title()} Quick Apply Complete",
            'is_prod': django_settings.IS_PROD,
        },
    )


def programs(request):
    if request.method == "POST":
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
            ))

        # Create a EligibilityProgram object for the program_rearch with the program_name = 'identification'
        selected_eligibility_programs.append(EligibilityProgram(
            user_id=request.user.id,
            program_id=EligibilityProgramRD.objects.get(
                program_name='identification').id,
        ))
        EligibilityProgram.objects.bulk_create(
            selected_eligibility_programs)
        return redirect(reverse("app:files"))
    else:
        # Get all of the programs (except the one with identification and where is_active is False) from the application_EligibilityProgramRD table
        # ordered by the friendly_name field acending
        programs = EligibilityProgramRD.objects.filter(~Q(program_name='identification')).filter(
            is_active=True).order_by('friendly_name')

    return render(
        request,
        'programs.html',
        {
            'programs': programs,
            'step': 4,
            'form_page_number': form_page_number,
            'title': "Programs",
            'is_prod': django_settings.IS_PROD,
        },
    )


def not_available(request):
    return render(
        request,
        'not_available.html',
        {
            'title': "Address Not in Service Area",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_available(request):
    return render(
        request,
        'quick_available.html',
        {
            'title': "Quick Connexion Available",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_not_available(request):
    return render(
        request,
        'quick_not_available.html',
        {
            'title': "Quick Connexion Not Available",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_not_found(request):
    return render(
        request,
        'quick_not_found.html',
        {
            'title': "Quick Connexion Not Found",
            'is_prod': django_settings.IS_PROD,
        },
    )


def quick_coming_soon(request):

    if request.method == "POST":
        form = FutureEmailForm(request.POST or None)
        if form.is_valid():
            try:
                form.save()
            except AttributeError:
                print("Error Email Saving")
            else:
                request.session['connexion_communication'] = form.cleaned_data['connexion_communication']
                return redirect(reverse("app:account"))

    form = FutureEmailForm()
    return render(
        request,
        'quick_coming_soon.html',
        {
            'form': form,
            'model_url': reverse("app:quick_coming_soon"),
            'title': "Quick Connexion Coming Soon",
            'is_prod': django_settings.IS_PROD,
        },
    )


def coming_soon(request):

    if request.method == "POST":
        form = FutureEmailForm(request.POST or None)
        if form.is_valid():
            try:
                form.save()

                doEnroll = form.cleaned_data['connexion_communication']
                enrollFailure = False
                if doEnroll is True:
                    try:
                        enroll_connexion_updates(request)
                    except AssertionError:
                        enrollFailure = True

                return render(
                    request,
                    "quick_apply.html",
                    {
                        'programName': 'Reduced-Rate Connexion',
                        'enroll_failure': enrollFailure,
                        'is_enrolled': doEnroll,
                        'title': "Reduced-Rate Connexion Quick Apply Complete",
                        'is_prod': django_settings.IS_PROD,
                    },
                )

            except AttributeError:
                print("Error Email Saving")

    # If this application was started with quick_coming_soon and the address
    # entered there matches the application, skip to quick_apply.html
    if 'address_dict' in request.session.keys() and 'connexion_communication' in request.session.keys():
        addr = request.user.addresses
        if request.session['address_dict']['address'] == addr.address and request.session['address_dict']['zipCode'] == str(addr.zipCode):

            doEnroll = request.session['connexion_communication']
            enrollFailure = False
            if doEnroll is True:
                try:
                    enroll_connexion_updates(request)
                except AssertionError:
                    enrollFailure = True

            # Remove the session vars after use
            del request.session['address_dict']
            del request.session['connexion_communication']

            return render(
                request,
                "quick_apply.html",
                {
                    'programName': 'Reduced-Rate Connexion',
                    'enroll_failure': enrollFailure,
                    'is_enrolled': doEnroll,
                    'title': "Reduced-Rate Connexion Quick Apply Complete",
                    'is_prod': django_settings.IS_PROD,
                },
            )

    form = FutureEmailForm()
    return render(
        request,
        'coming_soon.html',
        {
            'form': form,
            'model_url': reverse("app:coming_soon"),
            'title': "Reduced-Rate Connexion Communication",
            'is_prod': django_settings.IS_PROD,
        },
    )


def privacy_policy(request):
    # check if user is logged in
    user_logged_in = False
    if request.user.is_authenticated:
        user_logged_in = True

    return render(
        request,
        'privacy_policy.html',
        {
            'is_prod': django_settings.IS_PROD,
            'user_logged_in': user_logged_in,
        },
    )


def household_definition(request):
    return render(
        request,
        'household_definition.html',
        {
            'is_prod': django_settings.IS_PROD,
        },
    )


@set_update_mode
def files(request):
    '''
    Variables:
    fileNames - used to name the files in the database and file upload
    fileAmount - number of file uploads per income verified documentation
    '''
    users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
        request)

    if request.method == "POST":
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
                # filetype = magic.from_file("mobileVers/" + instance.document.url)
                filetype = magic.from_buffer(f.read())
                logging.info(filetype)

                # Check if any of the following strings ("PNG", "JPEG", "JPG", "PDF") are in the filetype
                if any(x in filetype for x in ["PNG", "JPEG", "JPG", "PDF"]):
                    pass
                else:
                    logging.error(
                        "File is not a valid file type. file is: " + filetype)
                    users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
                        request)
                    return render(
                        request,
                        'files.html',
                        {
                            "message": "File is not a valid file type. Please upload either  JPG, PNG, OR PDF.",
                            'form': form,
                            'eligiblity_programs': users_programs_without_uploads,
                            'step': 5,
                            'form_page_number': form_page_number,
                            'title': "Files",
                            'file_upload': json.dumps({'success_status': False}),
                            'is_prod': django_settings.IS_PROD,
                        },
                    )

            for f in request.FILES.getlist('document_path'):
                fileAmount += 1
                # this line allows us to save multiple files: format = iso format (f,f) = (name of file, actual file)
                instance.document_path.save(datetime.datetime.now(
                ).isoformat() + "_" + str(fileAmount) + "_" + str(f), f)
                fileNames.append(str(instance.document_path))
                # Below is blob / storage code for Azure! Files automatically uploaded to the storage
                f.seek(0)
                blob_storage_upload(str(instance.document_path.url), f)

            # below the code to update the database to allow for MULTIPLE files AND change the name of the database upload!
            instance.document_path = str(fileNames)
            instance.save()

            users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
                request)
            if users_programs_without_uploads.count():
                return render(
                    request,
                    'files.html',
                    {
                        'form': form,
                        'eligiblity_programs': users_programs_without_uploads,
                        'step': 5,
                        'form_page_number': form_page_number,
                        'title': "Files",
                        'file_upload': json.dumps({'success_status': True}),
                        'is_prod': django_settings.IS_PROD,
                    },
                )
            else:
                # Get all of the user's eligiblity programs and find the one with the lowest 'ami_threshold' value
                # which can be found in the related eligiblityprogramrd table
                lowest_ami = EligibilityProgram.objects.filter(
                    Q(user_id=request.user.id)
                ).select_related('program').values('program__ami_threshold').order_by('program__ami_threshold').first()

                # Now save the value of the ami_threshold to the user's household
                Household.objects.filter(
                    Q(user_id=request.user.id)
                ).update(ami_range_min=lowest_ami['program__ami_threshold'], ami_range_max=lowest_ami['program__ami_threshold'])

                return redirect(reverse("app:broadcast"))
    else:
        form = FileUploadForm()
        return render(
            request,
            'files.html',
            {
                'form': form,
                'eligiblity_programs': users_programs_without_uploads,
                'step': 5,
                'form_page_number': form_page_number,
                'title': "Files",
                'file_upload': json.dumps({'success_status': None}),
                'is_prod': django_settings.IS_PROD,
            },
        )


def broadcast(request):
    current_user = request.user
    try:
        broadcast_email(current_user.email)
    except:
        logging.error("there was a problem with sending the email / sendgrid")
        # TODO store / save for later: client getting feedback that SendGrid may be down
    phone = str(current_user.phone_number)
    try:
        broadcast_sms(phone)
    except:
        logging.error("Twilio servers may be down")
        # TODO store / save for later: client getting feedback that twilio may be down
    return render(
        request,
        'broadcast.html',
        {
            'program_string': current_user.email,
            'step': 6,
            'form_page_number': form_page_number,
            'title': "Broadcast",
            'is_prod': django_settings.IS_PROD,
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
        'user_settings.html',
        {
            "name": request.user.first_name,
            "lastName": request.user.last_name,
            "email": request.user.email,
            'is_prod': django_settings.IS_PROD,
            "routes": {
                "account": reverse('app:account'),
                "household": reverse('app:household'),
            },
            "page_updated": json.dumps({'page_updated': page_updated}, cls=DjangoJSONEncoder),
        },
    )


def password_reset_request(request):
    User = get_user_model()
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    email_template_name = "PasswordReset/password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': 'getfoco.fcgov.com',  # 'getfoco.azurewebsites.net' | '127.0.0.1:8000'
                        'site_name': 'Get FoCo',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        #                        send_mail(subject, email, 'admin@example.com' , [user.email], fail_silently=False)
                        broadcast_email_pw_reset(user.email, email)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                    return redirect("/password_reset/done/")
    password_reset_form = PasswordResetForm()

    return render(
        request,
        "PasswordReset/password_reset.html",
        {
            "password_reset_form": password_reset_form,
            'title': "Password Reset Request",
            'is_prod': django_settings.IS_PROD,
        },
    )


def login_user(request):
    if request.method == "POST":
        # Try to log in user
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(username=email, password=password)
        # Check if the authentication was successful
        if user is not None:
            login(request, user)
            # Push user to correct page
            # update application_user "modified" per login
            obj = request.user
            obj.save()
            # Push user to correct page
            page = what_page(request.user, request)
            print(page)
            if page == "app:dashboard":
                return redirect(reverse("app:dashboard"))
            else:
                return redirect(reverse("app:notify_remaining"))

        else:
            return render(
                request,
                "login.html",
                {
                    "message": "Invalid username and/or password",
                    'title': "Login",
                    'is_prod': django_settings.IS_PROD,
                },
            )

    # If it turns out user is already logged in but is trying to log in again,
    # run through what_page() to find the correct place
    if request.method == "GET" and request.user.is_authenticated:
        page = what_page(request.user, request)
        print(page)
        if page == "app:dashboard":
            return redirect(reverse("app:dashboard"))
        else:
            return redirect(reverse("app:notify_remaining"))

    # Just give back log in page if none of the above is true
    else:
        return render(
            request,
            "login.html",
            {
                'title': "Login",
                'is_prod': django_settings.IS_PROD,
            },
        )


def notify_remaining(request):
    page = what_page(request.user, request)
    return render(
        request,
        "notify_remaining.html",
        {
            "next_page": page,
            'title': "Notify Remaining Steps",
            'is_prod': django_settings.IS_PROD,
        },
    )


def qualified_programs(request):
    programs = get_users_iq_programs(
        request.user.id, request.user.household.ami_range_max)

    order_by = request.GET.get('order_by')
    if order_by and order_by == 'eligible':
        programs = sorted(programs, key=lambda x: (
            x.status_for_user, x.status_for_user))
    elif order_by:
        programs = sorted(programs, key=lambda x: (
            x.status_for_user.lower() != order_by, x.status_for_user))

    return render(
        request,
        'qualified_programs.html',
        {
            "title": "Qualified Programs",
            "dashboard_color": "white",
            "program_list_color": "var(--yellow)",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            "iq_programs": programs,
            'is_prod': django_settings.IS_PROD,
        },
    )


def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("app:feedback_received"))
        else:
            print("form is not valid")
    else:
        form = FeedbackForm()
    if request.user.eligibility.GenericQualified == QualificationStatus.PENDING.name or request.user.eligibility.GenericQualified == QualificationStatus.ACTIVE.name:
        text = "Based on your information, you may qualify! Be on the lookout for an email or phone call."
        text2 = "Based on your information you may also qualify for the city's Grocery Rebate Tax program!"
        text3 = "By clicking on the link below, we can send your information over and quick apply for you."
        text4 = "Click here to quick apply for Grocery Rebate Tax Program"
        text5 = ""
        text6 = "Click here to quick apply for Recreation"
        text7 = "The Get FoCo Office is working on a timeline to respond to applications within the next two weeks."
    else:
        text = "Based on your info, you may be over the pre-tax income limit. At this time you do not qualify. If your income changes, please apply again."
        text2 = ""
        text3 = ""
        text4 = ""
        text5 = "Grocery Rebate Tax Program"
        text6 = "Utilities Income-Qualified Assistance Program"
        text7 = "The Get FoCo Office is working on a timeline to respond to applications within the next two weeks."

    if request.user.eligibility.GRqualified == QualificationStatus.PENDING.name or request.user.eligibility.GRqualified == QualificationStatus.ACTIVE.name:
        text2 = "Thank you for quick applying for the Grocery Rebate Tax Program."
        text3 = "Expect an update within 3 weeks - check your email!"
        text4 = ""

    return render(
        request,
        'index.html',
        context={
            "program_string": text,
            "program_string2": text2,
            "program_string3": text3,
            "program_string4": text4,
            "program_string5": text5,
            "program_string6": text6,
            "program_string7": text7,
            'title': "Feedback",
            'is_prod': django_settings.IS_PROD,
        },
    )


def feedback_received(request):
    return render(
        request,
        "feedback_received.html",
        {
            'title': "Feedback Received",
            'is_prod': django_settings.IS_PROD,
        },
    )


def dashboard(request):
    request.session['update_mode'] = False
    qualified_programs = 0
    active_programs = 0
    pending_programs = 0

    iq_programs = get_users_iq_programs(
        request.user.id, request.user.household.ami_range_max)
    for program in iq_programs:
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
        'dashboard.html',
        {
            "title": "Get FoCo Dashboard",
            "dashboard_color": "var(--yellow)",
            "program_list_color": "white",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            "iq_programs": iq_programs,
            "qualified_programs": qualified_programs,
            "pending_programs": pending_programs,
            "active_programs": active_programs,
            "clientName": request.user.first_name,
            "clientEmail": request.user.email,
            'is_prod': django_settings.IS_PROD,
            'proxy_viewed_dashboard': proxy_viewed_dashboard,
            'badge_visible': request.user.household.is_income_verified,
        },
    )


def programs_list(request):
    programs = get_users_iq_programs(
        request.user.id, request.user.household.ami_range_max)
    return render(
        request,
        'programs_list.html',
        {
            "page_title": "Programs List",
            "dashboard_color": "white",
            "program_list_color": "var(--yellow)",
            "Settings_color": "white",
            "Privacy_Policy_color": "white",
            'title': "Programs List",
            'is_prod': django_settings.IS_PROD,
            'iq_programs': programs,
        },
    )


def programs_info(request):
    return render(
        request,
        'programs_info.html',
        {
            'title': "Programs List",
            'is_prod': django_settings.IS_PROD,
            'iq_programs': IQProgramRD.objects.all(),
        },
    )
