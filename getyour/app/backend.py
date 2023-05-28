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
from decimal import Decimal
import json
import hashlib
import datetime
import urllib.parse
import requests
from azure.storage.blob import BlockBlobService
from twilio.rest import Client
from sendgrid.helpers.mail import Mail
from sendgrid import SendGridAPIClient
from usps import USPSApi, Address
from itertools import chain
from django import http
from django.shortcuts import reverse
from django.contrib.auth.backends import UserModel
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from app.models import HouseholdMembers, EligibilityProgram, IQProgramRD, IQProgram


def broadcast_sms(phone_Number):
    message_to_broadcast = (
        "Thank you for creating an account with Get FoCo! Be sure to review the programs you qualify for on your dashboard and click on Apply Now to finish the application process!")
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(to=phone_Number,
                           from_=settings.TWILIO_NUMBER,
                           body=message_to_broadcast)


def address_check(address_dict):
    """
    Check for address GMA and Connexion statuses.

    Parameters
    ----------
    instance : dict
        Post-USPS-validation dictionary. Usable data for this script are in
        ['AddressValidateResponse']['Address'][...].

    Returns
    -------
    bool
        Whether the address is in the GMA (True, False).
    bool
        The status of Connexion service (True, False, None).

    """

    try:
        # Gather the coordinate string for future queries
        # Parse the 'instance' data for proper 'address_parts'
        address_parts = "{}, {}".format(
            address_dict['AddressValidateResponse']['Address']['Address2'],
            address_dict['AddressValidateResponse']['Address']['Zip5'],
        )
        coord_string = address_lookup(address_parts)

    except NameError:
        # NameError specifies that the address is not found
        # in City lookups and is therefore not in the IQ
        # service area
        return (False, False)

    else:
        has_connexion = connexion_lookup(coord_string)
        print('No Connexion for you') if has_connexion is None else print(
            'Connexion available') if has_connexion else print('Connexion coming soon')

        is_in_gma = gma_lookup(coord_string)
        print('Is in GMA!') if is_in_gma else print('Outside of GMA')

        return (is_in_gma, has_connexion)


def address_lookup(address_parts):
    """
    Look up the coordinates for an address to input into future queries.

    Parameters
    ----------
    address_parts : str
        The address parts to use for the lookup (specifically in the format
        <address_2>, <zip code>) (e.g. "300 LAPORTE AVE, 80521", sans quotes).

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.
    NameError
        Address not found in City lookups - address is not in IQ service area.

    Returns
    -------
    str
        Formatted string of x,y coordinates for the address, to input in
        future queries.

    """

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/Geocode/Fort_Collins_Area_Address_Point_Geocoding_Service/GeocodeServer/findAddressCandidates'

    payload = {
        'f': 'pjson',
        'Street': address_parts,
    }

    # Gather response
    response = requests.get(url, params=payload)
    if response.status_code != requests.codes.ok:
        raise requests.exceptions.HTTPError(response.reason, response.content)

    # Parse response
    outVal = response.json()

    # Ensure candidate(s) exist and they have a decent match score
    # Because this is how the Sales Tax lookup is architected, it should be
    # safe to assume these are returned sorted, with best candidate first
    if len(outVal['candidates']) > 0 and outVal['candidates'][0]['score'] > 85:
        # Define the coordinate string to be used in future queries
        coord_string = '{x},{y}'.format(
            x=outVal['candidates'][0]['location']['x'],
            y=outVal['candidates'][0]['location']['y'],
        )

    else:
        raise NameError("Matching address not found")

    return coord_string


def connexion_lookup(coord_string):
    """
    Look up the Connexion service status given the coordinate string.

    Parameters
    ----------
    coord_string : str
        Formatted <x>,<y> string of coordinates from address_lookup().

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.
    IndexError
        Address not found in Connexion lookups - Connexion is likely to be
        unavailable at this address.

    Returns
    -------
    bool
        Boolean 'status', designating True for 'service available' or False
        for 'service will be available, but not yet' OR None for 'unavailable'
        (probably)

    TODO: Switch this to an enum if we want to keep this structure

    """

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/FDH_Boundaries_ForPublic/MapServer/0/query'

    payload = {
        'f': 'pjson',
        'geometryType': 'esriGeometryPoint',
        'geometry': coord_string,
    }

    # Gather response
    response = requests.post(url, params=payload)
    if response.status_code != requests.codes.ok:
        raise requests.exceptions.HTTPError(response.reason, response.content)

    # Parse response
    outVal = response.json()

    try:
        statusInput = outVal['features'][0]['attributes']['INVENTORY_STATUS_CODE']

    except (IndexError, KeyError):
        return None

    else:
        statusInput = statusInput.lower()

        # If we made it to this point, Connexion will be or is currently
        # available
        if statusInput in (
                'released',
                'out of warranty',
        ):      # this is the 'available' case
            return True

        else:
            return False


def gma_lookup(coord_string):
    """
    Look up the GMA location given the coordinate string.

    Parameters
    ----------
    coord_string : str
        Formatted <x>,<y> string of coordinates from address_lookup().

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.    

    Returns
    -------
    Boolean 'status', designating True for an address within the GMA, or False
    otherwise.

    """

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/FCMaps/MapServer/26/query'

    payload = {
        # Manually stringify 'geometry' - requests and json.dumps do this
        # incorrectly
        'geometry': """{"points":[["""+coord_string+"""]],"spatialReference":{"wkid":102653}}""",
        'geometryType': 'esriGeometryMultipoint',
        'inSR': 2231,
        'spatialRel': 'esriSpatialRelIntersects',
        'where': '',
        'returnGeometry': 'false',
        'outSR': 2231,
        'outFields': '*',
        'f': 'pjson',
    }

    # Gather response
    response = requests.get(url, params=payload)
    if response.status_code != requests.codes.ok:
        raise requests.exceptions.HTTPError(response.reason, response.content)

    # Parse response
    outVal = response.json()

    if len(outVal['features']) > 0:
        return True
    else:
        return False


def validate_usps(inobj):
    if isinstance(inobj, http.request.QueryDict):
        # Combine fields into Address
        address = Address(
            name=" ",
            address_1=inobj['address'],
            address_2=inobj['address2'],
            city=inobj['city'],
            state=inobj['state'],
            zipcode=inobj['zipcode'],
        )

    elif isinstance(inobj, dict):
        address = Address(**inobj)

    else:
        raise AttributeError('Unknown validation input')

    usps = USPSApi(settings.USPS_SID, test=True)
    validation = usps.validate_address(address)
    outDict = validation.result
    try:
        print(outDict['AddressValidateResponse']['Address']['Address2'])
        print(outDict)
        return outDict

    except KeyError:
        print("Address could not be found - no guesses")
        raise


def broadcast_email(email):
    TEMPLATE_ID = settings.TEMPLATE_ID
    message = Mail(
        from_email='getfoco@fcgov.com',
        to_emails=email)

    message.template_id = TEMPLATE_ID
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


def broadcast_email_pw_reset(email, content):
    TEMPLATE_ID_PW_RESET = settings.TEMPLATE_ID_PW_RESET
    message = Mail(
        subject='Password Reset Requested',
        from_email='getfoco@fcgov.com',
        to_emails=email,
    )
    message.dynamic_template_data = {
        'subject': 'Password Reset Requested',
        'html_content': content,
    }
    message.template_id = TEMPLATE_ID_PW_RESET
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


def model_to_dict(model):
    """
    Convert a model object to a dictionary. If a property is a datetime object,
    it will be converted to a string. If there is a nested model, it will be
    excluded from the dictionary.
    :param model: model object
    """
    model_dict = {}
    for field in model._meta.get_fields():
        if field.is_relation:
            continue
        value = getattr(model, field.name)
        if isinstance(value, datetime.datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        model_dict[field.name] = value
    return model_dict


def serialize_household_members(request):
    """
    Serialize the household members from the request body. Into a list of dictionaries.
    then convert the list of dictionaries into json, so it can be stored in the users
    household_info. Each dictionary should have a 'name' and 'birthdate
    :param request: request object
    """
    # Parse the form data from the request body into a dictionary
    data = urllib.parse.parse_qs(request.body.decode('utf-8'))

    # Extract the household member data and exclude csrfmiddlewaretoken
    household_members_data = {k: v for k,
                              v in data.items() if k != 'csrfmiddlewaretoken'}

    # Create a list of dictionaries with 'name' and 'birthdate' keys
    household_members = [{'name': data['name'][i], 'birthdate': data['birthdate'][i]}
                         for i in range(len(household_members_data['name']))]

    household_info = json.loads(json.dumps(
        {'persons_in_household': household_members}, cls=DjangoJSONEncoder))
    return household_info


def blob_storage_upload(filename, file):
    blob_service_client = BlockBlobService(
        account_name=settings.BLOB_STORE_NAME,
        account_key=settings.BLOB_STORE_KEY,
        endpoint_suffix=settings.BLOB_STORE_SUFFIX,
    )

    blob_service_client.create_blob_from_bytes(
        container_name=settings.USER_FILES_CONTAINER,
        blob_name=filename,
        blob=file.read(),
    )


def authenticate(username=None, password=None):
    User = get_user_model()
    try:  # to allow authentication through phone number or any other field, modify the below statement
        user = User.objects.get(email=username)
        print(user)
        print(password)
        print(user.password)
        print(user.check_password(password))
        if user.check_password(password):
            return user
        return None
    except User.DoesNotExist:
        return None


def get_user(user_id):
    try:
        return UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return None


def what_page(user, request):
    """
    Redirect user to whatever page they need to go to every time by checking which steps they've
    completed in the application process
    """
    if user.is_authenticated:
        # for some reason, none of these login correctly... reviewing this now
        try:  # check if the addresses.is_verified==True
            request.user.address
        except AttributeError:
            return "app:address"

        try:
            request.user.household
        except AttributeError:
            return "app:household"

        if (HouseholdMembers.objects.all().filter(user_id=request.user.id).exists()):
            pass
        else:
            return "app:household_members"

        # Check to see if the user has selected any eligibility programs
        if (request.user.eligibility_files.count()):
            pass
        else:
            return "app:programs"

        users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
            request)
        if users_programs_without_uploads.count():
            return "app:files"

        return "app:dashboard"
    else:
        return "app:account"


def build_qualification_button(users_enrollment_status):
    # Create a dictionary to hold the button information
    return {
        'PENDING': {
            "text": "Applied",
            "color": "green",
            "textColor": "white"
        },
        'ACTIVE': {
            "text": "Enrolled!",
            "color": "blue",
            "textColor": "white"
        },
        '': {
            "text": "Apply Now +",
            "color": "",
            "textColor": ""
        },
    }.get(users_enrollment_status, "")


def map_iq_enrollment_status(program):
    try:
        if program.is_enrolled:
            return "ACTIVE"
        else:
            return "PENDING"
    except Exception:
        return ''


def get_users_iq_programs(user_id, users_ami_range_max, users_eligiblity_address):
    """ 
    Get the iq programs for the user where the user is geographically eligible, as well as 
    where their ami range is less than or equal to the users max ami range
    or where the user has already applied to the program. Additionaly filter out
    params:
        user_id: the id of the user
        users_ami_range_max: the max ami range for the user
        users_eligiblity_address: the eligibility address for the user
    returns:
        a list of users iq programs
    """
    # Get the IQ programs that a user has already applied to
    users_iq_programs = list(IQProgram.objects.select_related(
        'program').filter(user_id=user_id))

    # Get the IQ programs a user is eligible for
    users_iq_programs_ids = [
        program.program_id for program in users_iq_programs]
    active_iq_programs = list(IQProgramRD.objects.filter(
        (Q(is_active=True) & Q(ami_threshold__gte=Decimal(
            float(users_ami_range_max))) & ~Q(id__in=users_iq_programs_ids))
    ))

    # Filter out the active programs that the user is not geographically eligible for.
    # If the IQ program's req_is_city_covered is true, then check to make sure
    # the user's eligibility address is_city_covered.
    active_iq_programs = [
        program for program in active_iq_programs if not (program.req_is_city_covered and not users_eligiblity_address.is_city_covered)]

    programs = list(chain(users_iq_programs, active_iq_programs))
    for program in programs:
        status_for_user = map_iq_enrollment_status(program)
        program.button = build_qualification_button(
            status_for_user)
        program.status_for_user = status_for_user
        program.quick_apply_link = reverse('app:quick_apply', kwargs={
                                           'iq_program': program.program.program_name if hasattr(program, 'program') else program.program_name})
        program.title = program.program.friendly_name if hasattr(
            program, 'program') else program.friendly_name
        program.subtitle = program.program.friendly_category if hasattr(
            program, 'program') else program.friendly_category
        program.description = program.program.friendly_description if hasattr(
            program, 'program') else program.friendly_description
        program.supplemental_info = program.program.friendly_supplemental_info if hasattr(
            program, 'program') else program.friendly_supplemental_info
        program.eligibility_review_status = 'We are reviewing your application! Stay tuned here and check your email for updates.' if status_for_user == 'PENDING' else '',
        program.eligibility_review_time_period = program.program.friendly_eligibility_review_period if hasattr(
            program, 'program') else program.friendly_eligibility_review_period
        program.learn_more_link = program.program.learn_more_link if hasattr(
            program, 'program') else program.learn_more_link
        program.autoapply_ami_threshold = program.program.autoapply_ami_threshold if hasattr(
            program, 'program') else program.autoapply_ami_threshold
        program.ami_threshold = program.program.ami_threshold if hasattr(
            program, 'program') else program.ami_threshold
    return programs


def get_in_progress_eligiblity_file_uploads(request):
    """Returns a list of eligibility programs that are in progress. This is just a shim for now
    and will eventually be replaced by a call to the database through Django's ORM
    Returns:
        list: List of eligibility programs
    """
    users_in_progress_file_uploads = EligibilityProgram.objects.filter(
        Q(user_id=request.user.id) & Q(document_path='')
    ).select_related('program').values('id', 'program__id', 'program__friendly_name')
    return users_in_progress_file_uploads
