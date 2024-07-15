"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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
import datetime
import requests
import pendulum
from enum import Enum
from typing import Union
from itertools import chain
import logging
import httpagentparser
import magic

from twilio.rest import Client
from sendgrid.helpers.mail import Mail
from sendgrid import SendGridAPIClient
from usps import USPSApi, Address

from python_http_client.exceptions import HTTPError as SendGridHTTPError
from twilio.base.exceptions import TwilioRestException

from django import http
from django.shortcuts import reverse
from django.contrib.auth.backends import UserModel
from django.contrib.auth import login as django_auth_login
from django.conf import settings
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.fields.files import FieldFile
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files.uploadedfile import UploadedFile
from phonenumber_field.phonenumber import PhoneNumber
from app.models import (
    HouseholdMembers,
    EligibilityProgram,
    IQProgramRD,
    IQProgram,
    User,
    Household,
    AddressRD,
)
from app.constants import (
    supported_content_types,
    enable_calendar_year_renewal,
    application_pages,
)
from logger.wrappers import LoggerWrapper


# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


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


class QualificationStatus(Enum):
    NOTQUALIFIED = 'NOT QUALIFIED'
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'


def broadcast_sms(phone_Number):
    message_to_broadcast = (
        "Thank you for creating an account with Get FoCo! Be sure to review the programs you qualify for on your dashboard and click on Apply Now to finish the application process!")
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        message_instance = client.messages.create(
            to=phone_Number,
            from_=settings.TWILIO_NUMBER,
            body=message_to_broadcast,
        )
    except TwilioRestException as e:
        log.exception(e, function='broadcast_sms')


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
        # in City lookups and is therefore *probably* not in the IQ
        # service area

        # Log a potential error if the city is 'Fort Collins'
        if address_dict['AddressValidateResponse']['Address']['City'].lower() == 'fort collins':    
            log.error(
                "Potential issue: Fort Collins address marked 'not in GMA': {}".format(
                    address_dict['AddressValidateResponse']['Address'],
                ),
                function='address_check',
            )

        return (False, False)

    else:
        has_connexion = connexion_lookup(coord_string)
        msg = 'Connexion not available or API not found' if has_connexion is None \
            else 'Connexion available' if has_connexion \
            else 'Connexion coming soon'
        log.info(msg, function='address_check')

        is_in_gma = gma_lookup(coord_string)
        msg = 'Address is in GMA' if is_in_gma else 'Address is outside of GMA'
        log.info(msg, function='address_check')

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
        log.error(
            f"API error {response.status_code}: {response.reason}; {response.content}",
            function='address_lookup',
        )
        raise requests.exceptions.HTTPError(response.reason, response.content)

    # Parse response
    outVal = response.json()

    # Since the gisweb endpoint seems to always return an HTTP 200, also check
    # the JSON for an 'error' key
    if 'error' in outVal:
        errDict = outVal['error']
        log.error(
            f"API error {errDict['code']}: {errDict['message']}",
            function='address_lookup',
        )
        raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

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

    try:
        # Gather response
        response = requests.post(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function='connexion_lookup',
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if 'error' in outVal:
            errDict = outVal['error']
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function='connexion_lookup',
            )
            raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

        statusInput = outVal['features'][0]['attributes']['INVENTORY_STATUS_CODE']

    except requests.exceptions.HTTPError:
        return None

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

    try:
        # Gather response
        response = requests.get(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function='gma_lookup',
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if 'error' in outVal:
            errDict = outVal['error']
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function='gma_lookup',
            )
            raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

        if len(outVal['features']) > 0:
            return True
        else:
            return False

    except requests.exceptions.HTTPError:
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
        log.info(
            f"Address dict found: {outDict}",
            function='validate_usps',
        )
        return outDict

    except KeyError:
        log.exception(
            "Address could not be found - no guesses",
            function='validate_usps',
        )
        raise


def broadcast_email(email):
    message = Mail(
        from_email=settings.CONTACT_EMAIL,
        to_emails=email)

    message.template_id = settings.WELCOME_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned HTTP {response.status_code}",
            function='broadcast_email',
        )
    except Exception as e:
        log.exception(e, function='broadcast_email')


def broadcast_email_pw_reset(email, content):
    message = Mail(
        subject='Password Reset Requested',
        from_email=settings.CONTACT_EMAIL,
        to_emails=email,
    )
    message.dynamic_template_data = {
        'subject': 'Password Reset Requested',
        'html_content': content,
    }
    message.template_id = settings.PW_RESET_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned HTTP {response.status_code}",
            function='broadcast_email_pw_reset',
        )
    except Exception as e:
        log.exception(
            e,
            function='broadcast_email_pw_reset',
        )


def broadcast_renewal_email(email):
    message = Mail(
        from_email=settings.CONTACT_EMAIL,
        to_emails=email)

    message.template_id = settings.RENEWAL_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned: HTTP {response.status_code}",
            function='broadcast_renewal_email',
        )

    except SendGridHTTPError as response:
        log.exception(
            f"Sendgrid returned: {response}",
            function='broadcast_renewal_email',
        )

    return response.status_code


def changed_modelfields_to_dict(
        previous_instance,
        current_instance,
        pre_delete=False,
):
    """
    Convert a model object to a dictionary. If a property is a datetime object,
    it will be converted to a string. If there is a nested model, it will be
    excluded from the dictionary. If pre_delete is True, the previous instance
    is returned as a dictionary.
    :param previous_instance: model object
    :param current_instance: model object
    :param pre_delete: boolean
    """

    # Initialize output
    model_dict = {}

    if pre_delete:
        # Save all fields as dictionary before deleting the record
        for field in previous_instance._meta.fields:
            field_name = field.name
            try:
                value = getattr(previous_instance, field_name)
                if field.is_relation:
                    # Designate the field name and value as 'id'
                    model_dict[f"{field.name}_id"] = value.id
                elif isinstance(value, FieldFile):
                    # save the value so it can be json serialized
                    model_dict[field.name] = str(value)
                else:
                    if isinstance(value, datetime.datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, PhoneNumber):
                        value = value.as_e164
                    model_dict[field.name] = value

            except AttributeError:
                pass
    else:
        # Compare the current instance with the previous instance
        for field in current_instance._meta.fields:
            field_name = field.name
            if getattr(current_instance, field_name) != getattr(previous_instance, field_name):
                try:
                    value = getattr(previous_instance, field_name)
                    if field.is_relation:
                        # Designate the field name and value as 'id'
                        model_dict[f"{field.name}_id"] = value.id
                    # check if the field is FieldFile
                    elif isinstance(value, FieldFile):
                        # save the value so it can be json serialized
                        model_dict[field.name] = str(value)
                    else:
                        if isinstance(value, datetime.datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(value, PhoneNumber):
                            value = value.as_e164
                        model_dict[field.name] = value

                except AttributeError:
                    pass

    return model_dict


def serialize_household_members(request, file_paths):
    """
    Serialize the household members from the request body. Into a list of dictionaries.
    then convert the list of dictionaries into json, so it can be stored in the users
    household_info. Each dictionary should have a 'name' and 'birthdate
    :param request: request object
    """
    # Extract the household member data and exclude csrfmiddlewaretoken
    household_members_data = {
        k: request.POST.getlist(k)
        for k in request.POST.keys()
        if k != 'csrfmiddlewaretoken'
    }

    # Create a list of dictionaries with 'name' and 'birthdate' keys
    household_members = [{
        'name': household_members_data['name'][i],
        'birthdate': household_members_data['birthdate'][i],
        'identification_path': file_paths[i]
    } for i in range(len(household_members_data['name']))]

    household_info = json.loads(json.dumps(
        {'persons_in_household': household_members}, cls=DjangoJSONEncoder))
    return household_info
    

def login(request, user):

    django_auth_login(request, user)

    # Try to log user agent data
    try:
        log.info(
            "User logged in; agent is {}".format(
                httpagentparser.simple_detect(request.META['HTTP_USER_AGENT'])
            ),
            function='login',
            user_id=request.user.id,
        )
    except Exception:
        log.exception(
            "HTTP agent parsing failed!",
            function='login',
            user_id=request.user.id,
        )


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
        'RENEWAL': {
            "text": "Renew",
            "color": "orange",
            "textColor": "white"
        },
        '': {
            "text": "Apply Now",
            "color": "",
            "textColor": ""
        },
    }.get(users_enrollment_status, "")


def map_iq_enrollment_status(program, needs_renewal=False):
    try:
        # Check pending programs first. Reason being we don't want in progress
        # programs to be marked as renewal
        if not program.is_enrolled:
            return "PENDING"
        # If the user is enrolled in a "lifetime" program (i.e. a program that 
        # does not have a renewal_interval_year), don't set the status to
        # renewal
        elif program.is_enrolled and needs_renewal and program.renewal_interval_year is not None:
            return "RENEWAL"
        elif program.is_enrolled:
            return "ACTIVE"
        
    except Exception:
        return ''


def get_users_iq_programs(
        user_id,
        users_income_as_fraction_of_ami,
        users_eligiblity_address,
):
    """ 
    Get the iq programs for the user where the user is geographically eligible,
    as well as where their ami range is less than or equal to the users max ami
    range or where the user has already applied to the program. Additionaly
    filter out
    params:
        user_id: the id of the user
        users_income_as_fraction_of_ami: the user's household income as fraction
            of ami
        users_eligiblity_address: the eligibility address for the user
    returns:
        a list of users iq programs
    """
    # Get all (active) IQ programs that the user is eligible for (regardless of
    # application status). This accounts for both income and geographical
    # eligibility
    eligible_iq_programs = get_eligible_iq_programs(
        User.objects.get(id=user_id),
        users_eligiblity_address,
    )

    # Get the (active) IQ programs that a user has already applied to
    users_iq_programs = list(
        IQProgram.objects.select_related(
            'program',
        ).filter(
            user_id=user_id,
            program__is_active=True,
        ).order_by(
            'program__id'
        )
    )

    # Collapse any programs the user has already applied for into all programs
    # they are eligible for. The starting point is 'eligible programs' as
    # IQProgramRD objects, then any program the user is in gets converted to an
    # IQProgram object for later identification
    programs = []
    for prg in eligible_iq_programs:
        # Append the matching users_iq_programs element to programs if it
        # exists; else append the eligible_iq_programs element
        try:
            iq_program = next(x for x in users_iq_programs if x.program_id==prg.id)
        except StopIteration:
            programs.append(prg)
        else:
            programs.append(iq_program)

    # Determine if the user needs renewal for *any* program, and set as a user-
    # level 'needs renewal'
    needs_renewal = check_if_user_needs_to_renew(user_id)

    for program in programs:
        program.renewal_interval_year = program.program.renewal_interval_year if hasattr(
            program, 'program') else program.renewal_interval_year
        status_for_user = map_iq_enrollment_status(program, needs_renewal=needs_renewal)
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
        program.enable_autoapply = program.program.enable_autoapply if hasattr(
            program, 'program') else program.enable_autoapply
        program.ami_threshold = program.program.ami_threshold if hasattr(
            program, 'program') else program.ami_threshold
        program.id = program.program.id if hasattr(
            program, 'program') else program.id
    return programs


def get_eligible_iq_programs(
        user,
        eligibility_address,
    ):
    """ 
    Return IQ Programs that the user is eligible for, without accounting for
    current enrollment or program-specific application.
    
    """

    # Get all active IQ Programs with an AMI Threshold >= the user's income
    # fraction
    income_eligible_iq_programs = IQProgramRD.objects.filter(
        is_active=True,
        # If income_as_fraction_of_ami is None, set to 100% to exclude all programs
        ami_threshold__gte=user.household.income_as_fraction_of_ami or 1,
    ).order_by(
        'id'
    )

    # Gather all `requires_` fields in the IQProgramRD model along with their
    # corresponding AddressRD Boolean
    req_fields = get_iqprogram_requires_fields()

    # Filter programs further based on address requirements. Fields beginning
    # with `requires_` permissively specify whether the matching field in
    # AddressRD is a filter for the program, so a True value in the `requires_`
    # field requires the corresponding address Boolean to also be True to be
    # eligible, but because it's permissive, a False value in the `requires_`
    # field means that all addresses are eligible, regardless of the value of
    # the corresponding Boolean. Or as a truth table:

    # An address is eligible for benefits under the following conditions:
    #
    #                         ``requires_`` field
    #                         *TRUE*        *FALSE*
    # corresponding  *TRUE*    TRUE         TRUE
    #    Boolean     *FALSE*   FALSE        TRUE
    #
    # === ( (corresponding Boolean) OR NOT(`requires_`) )

    # Due to the permissive nature of the individual `requires_` fields,
    # multiple `requires_` criteria are then ANDed together for the overall
    # eligibility. For example, if no `requires_` fields are enabled, *all*
    # addresses are eligible (eligibility = True AND True AND True AND ... ==
    # True), but if any one of the `requires_` fields are enabled, an address is
    # ineligible if it doesn't meet that criteria (eligibility = True AND False
    # AND True AND ... == False)

    # For each program, take (<address Boolean> or not <requires_>) for all
    # `requires_` fields, and AND them together (via all())
    eligible_iq_programs = [
        prog for prog in income_eligible_iq_programs if all(
            (getattr(eligibility_address, cor) or not getattr(prog, req)) for req, cor in req_fields
        )
    ]

    return eligible_iq_programs


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


def save_renewal_action(request, action, status='completed', data={}):
    """Saves a renewal action to the database
    Args:
        request (HttpRequest): The request object
        action (str): The action to save
    """
    user = UserModel.objects.get(id=request.user.id)
    if hasattr(user, 'last_renewal_action'):
        last_renewal_action = user.last_renewal_action if user.last_renewal_action else {}

        # Check if the action exists in the last renewal action
        if action in last_renewal_action:
            last_renewal_action[action] = {'status': status, 'data': data}
        else:
            last_renewal_action[action] = {'status': status, 'data': data}

        user.last_renewal_action = json.loads(
            json.dumps(last_renewal_action, cls=DjangoJSONEncoder))
        user.save()


def what_page_renewal(last_renewal_action):
    """Returns the what page for the renewal flow
    Returns:
        str: The what page for the renewal flow
    """

    for page, url in application_pages.items():
        if page not in last_renewal_action:
            return url

    # Default return if all pages are present
    return None


def check_if_user_needs_to_renew(user_id):
    """Checks if the user needs to renew their application
    Args:
        user_id (int): The ID (primary key) of the User object
    Returns:
        bool: True if the user needs to renew their application, False otherwise
    """
    user_profile = User.objects.get(id=user_id)

    # Get the highest frequency renewal_interval_year from the IQProgramRD
    # table and filter out any null renewal_interval_year
    highest_freq_program = IQProgramRD.objects.filter(
        renewal_interval_year__isnull=False
    ).order_by('renewal_interval_year').first()
    
    # If there are no programs without lifetime enrollment (e.g. without
    # non-null renewal_interval_year), always return False for needs_renewal
    if highest_freq_program is None:
        return False
    
    highest_freq_renewal_interval = highest_freq_program.renewal_interval_year

    # The highest_freq_renewal_interval is measured in years. We need to check
    # if the user's next renewal date is greater than or equal to the current
    # date.
    needs_renewal = pendulum.instance(
        user_profile.last_completed_at).add(
        years=highest_freq_renewal_interval) <= pendulum.now()

    return needs_renewal


def finalize_application(user, renewal_mode=False, update_user=True):
    """
    Finalize the user's application. This is run after all Eligibility Program
    files are uploaded.

    The defaults are:
        - not in renewal_mode
        - do update the user object (last_completed_at, etc)
    
    """

    log.debug(
        f"Entering function with renewal_mode=={renewal_mode}",
        function='finalize_application',
        user_id=user.id,
    )

    # Get all of the user's eligiblity programs and find the one with the lowest
    # 'ami_threshold' value which can be found in the related
    # eligiblityprogramrd table
    lowest_ami = EligibilityProgram.objects.filter(
        Q(user_id=user.id)
    ).select_related(
        'program'
    ).values(
        'program__ami_threshold'
    ).order_by(
        'program__ami_threshold'
    ).first()

    # Now save the value of the ami_threshold to the user's household
    household = Household.objects.get(
        Q(user_id=user.id)
    )
    household.income_as_fraction_of_ami = lowest_ami['program__ami_threshold']

    if renewal_mode:
        household.is_income_verified = False
        household.save()

        # Set the user's last_completed_date to now, as well as set the user's
        # last_renewal_action to null
        if update_user:
            user = User.objects.get(id=user.id)
            user.renewal_mode = True
            user.last_completed_at = pendulum.now()
            user.last_renewal_action = None
            user.save()

        # Get every IQ program for the user that have a renewal_interval_year
        # in the IQProgramRD table that is not null
        users_current_iq_programs = IQProgram.objects.filter(
            Q(user_id=user.id)
        ).select_related(
            'program'
        ).order_by(
            'program__renewal_interval_year'
        ).exclude(
            program__renewal_interval_year__isnull=True
        )

        # For each element in users_current_iq_programs, delete the program.
        # Note that each element has a non-null renewal interval
        for program in users_current_iq_programs:
            program.renewal_mode = True
            program.delete()

        # Get the user's eligibility address
        eligibility_address = AddressRD.objects.filter(
            id=user.address.eligibility_address_id).first()

        # Now get all of the IQ Programs for which the user is eligible
        users_iq_programs = get_users_iq_programs(
            user.id,
            lowest_ami['program__ami_threshold'],
            eligibility_address,
        )

        # For each IQ program the user was previously enrolled, sort
        # eligibility status into renewal_eligible and renewal_ineligible
        renewal_eligible = []
        renewal_ineligible = []

        for program in users_current_iq_programs:
            if program.program.id in [x.id for x in users_iq_programs]:
                renewal_eligible.append(program.program.friendly_name)
            else:
                renewal_ineligible.append(program.program.friendly_name)

        # For every eligible IQ program, check if the user should be
        # automatically applied
        for program in users_iq_programs:
            # First, check if `program`` is in users_current_iq_programs; if so,
            # the user is both eligible and were previously applied/enrolled
            if program.id in [program.program.id for program in users_current_iq_programs]:
                # Re-apply by creating the element
                IQProgram.objects.create(
                    user_id=user.id,
                    program_id=program.id,
                )

            # Otherwise, apply if the program has enable_autoapply set to True
            elif program.enable_autoapply:
                # Check if the user already has the program in the IQProgram table
                if not IQProgram.objects.filter(
                    Q(user_id=user.id) & Q(
                        program_id=program.id)
                ).exists():
                    # If the user doesn't have the program in the IQProgram
                    # table, then create it
                    IQProgram.objects.create(
                        user_id=user.id,
                        program_id=program.id,
                    )

        # Return the target page and a dictionary of <session var>: <value>
        return (
            'app:dashboard',
            {
                'app_renewed': True,
                'renewal_eligible': sorted(renewal_eligible),
                'renewal_ineligible': sorted(renewal_ineligible),
            }
        )
    
    else:
        household.save()

        if update_user:
            user.last_completed_at = pendulum.now()
            user.save()

        # Get the user's eligibility address
        eligibility_address = AddressRD.objects.filter(
            id=user.address.eligibility_address_id).first()

        # Now get all of the IQ Programs for which the user is eligible
        users_iq_programs = get_users_iq_programs(
            user.id,
            lowest_ami['program__ami_threshold'],
            eligibility_address,
        )
        # For every IQ program, check if the user should be automatically
        # enrolled in it if the program has enable_autoapply set to True
        for program in users_iq_programs:
            # program is an IQProgramRD object only if the user has not applied
            if isinstance(program, IQProgramRD) and program.enable_autoapply:
                IQProgram.objects.create(
                    user_id=user.id,
                    program_id=program.id,
                )
                log.debug(
                    f"User auto-applied for '{program.program_name}' IQ program",
                    function='finalize_application',
                    user_id=user.id,
                )

        # Return the target page and an (empty) dictionary of <session var>: <value>
        return ('app:broadcast', {})


def enable_renew_now(user_id):
    """
    Enable the 'Renew Now' button on the dashboard pages
    """
    # Get the year from the last_completed_at of the user
    user_profile = User.objects.get(id=user_id)
    last_completed_at = user_profile.last_completed_at.year

    # Get the highest frequency renewal_interval_year from the IQProgramRD
    # table and filter out any null renewal_interval_year
    highest_freq_program = IQProgramRD.objects.filter(
        renewal_interval_year__isnull=False
    ).order_by('renewal_interval_year').first()

    # If there are no programs without lifetime enrollment (e.g. without
    # non-null renewal_interval_year), always return False
    if highest_freq_program is None:
        return False

    if enable_calendar_year_renewal and pendulum.now().year == last_completed_at + highest_freq_program.renewal_interval_year:
        return True
    else:
        return False


def get_iqprogram_requires_fields():
    """
    Gather all `requires_` fields in the IQProgramRD model along with their
    corresponding AddressRD Boolean.

    """
    field_prefix = 'requires_'
    req_fields = [
        (x.name, x.name.replace(field_prefix, '')) for x in IQProgramRD._meta.fields if x.name.startswith(field_prefix)
    ]

    return req_fields


def file_validation(
        obj,
        user_id,
        calling_function=None,
    ):
    """
    Validate the uploaded file with ``python-magic``.
    
    Returns a tuple of whether validation was successful and any error messages.
    
    """

    # If obj is an uploaded file, use the first chunk; else, take directly from
    # the buffer
    if isinstance(obj, UploadedFile):
        # If chunk_size is set manually here, python-magic recommends a minimum
        # size of 2048 bytes for proper filetype identification
        # (https://github.com/ahupp/python-magic?tab=readme-ov-file#usage)
        for itm in obj.chunks():
            filetype = magic.from_buffer(itm)
            break
    else:
        filetype = magic.from_buffer(obj)

    # Check if the filetype is in the supported_content_types
    matched_file_extension = next(
        (x for x in supported_content_types if x in filetype.lower()), None
    )
    # If a match is found, return 'success' and the file extension
    if matched_file_extension:
        return (True, matched_file_extension)
    
    # A match was not found, so return 'failed' and the error message
    log.error(
        "File{} is not a valid file type ({})".format(
            f" from {calling_function}" if calling_function else "",
            filetype,
        ),
        function='file_validation',
        user_id=user_id,
    )
    return (
        False,
        "File is not a valid type. Only these file types are supported: {}".format(
            ', '.join(supported_content_types)
        ),
    )


def finalize_address(instance, is_in_gma, has_connexion):
    """ Finalize the address, given inputs calculated earlier. """

    # Record the service area and Connexion status
    instance.is_in_gma = is_in_gma
    instance.is_city_covered = is_in_gma
    instance.has_connexion = has_connexion

    # Final step: mark the address record as 'verified' and save
    instance.is_verified = True
    instance.save()


def remove_ineligible_programs_for_user(user_id):
    """
    Remove programs that a user no longer qualifies for, based on application
    updates made after the user selected their programs.

    Note that this will throw an exception if any of the programs to be removed
    are currently-enrolled for the user, and no changes will be made.

    A use-case for this is when a user's documentation is changed from a 30% AMI
    eligibility program to a 60% AMI program via the admin panel.

    Parameters
    ----------
    user_id : int
        The ID of the target user.

    Returns
    -------
    str
        Returns the output message, with any compound messages joined by a
        semicolon.

    """

    # Get the user object (with updates that were presumably made just prior)
    user = User.objects.get(id=user_id).select_related('address')

    # Get the user's eligibility address
    eligibility_address = user.address.eligibility_address

    # Get the user's current programs
    users_iq_programs = IQProgram.objects.filter(user_id=user.id)

    # Get the programs the user is eligible for
    eligible_programs = get_eligible_iq_programs(
        user,
        eligibility_address,
    )

    # Compare current programs with eligible programs
    ineligible_current_programs = [
        x for x in users_iq_programs if x.program not in eligible_programs
    ]

    # Remove the user from the ineligible program(s), but ONLY IF they're not
    # currently enrolled

    # If a user is enrolled in any program, raise an exception
    enrolled_programs = [
        x for x in ineligible_current_programs if x.is_enrolled
    ]
    if len(enrolled_programs) > 0:
        raise AttributeError(
            "User is enrolled in {} but would no longer be eligible with the proposed change".format(
                ', '.join([x.program.program_name for x in enrolled_programs]),
            )
        )

    # Delete user from ineligible programs; return message describing the changes
    msg = []
    for prgrm in ineligible_current_programs:
        prgrm.delete()
        msg.append(f"User was removed from {prgrm.program.program_name}")

    return '; '.join(msg)


def update_users_for_program(
        *,  # force the following to be keyword-only parameters
        program: IQProgramRD,
        users: Union[list, tuple, QuerySet],
    ):
    """
    Update users' applicabilitiy for for the specified IQ Program, based on
    updates made after the user selected their programs. This will remove
    users from no-longer-eligible programs or auto-apply users to newly-eligible
    programs, where applicable.

    Note that this will ignore all users that are currently enrolled in the
    specified program. Any such users will be included in the function output.

    A use-case for this is when an IQ Program's requirements change and all
    active users must be modified for that program.

    Parameters
    ----------
    program : IQProgramRD
        The ID of the specified program.
    users : Union[list, tuple, QuerySet]
        A list, tuple, or queryset of User objects to be updated for the
        specified program. This can be a queryset of all users, but will slow
        the updates.

    Returns
    -------
    dict
        Returns a dictionary of counts of removed users and ignored users.

    """
    # Initialize output counts
    update_counts = {
        'applied_users': 0,
        'removed_users': 0,
        'ignored_users': 0,
    }

    # Loop through all User objects
    for usr in users:
        try:
            # Determine if the user is eligible (i.e. whether they should be
            # checked for auto-apply or for removal). ObjectDoesNotExist will be
            # thrown if the necessary information DNE for eligibility.
            user_eligible = program in get_eligible_iq_programs(
                usr,
                usr.address.eligibility_address,
            )

        except ObjectDoesNotExist:
            # Not all necessary information was found for eligibility, so there
            # is nothing further to do
            continue

        else:
            # Get the program if the user has applied for it (an
            # ObjectDoesNotExist exception will be thrown if the user hasn't
            # applied)
            try:
                applied_program = usr.iq_programs.get(program_id=program.id)

            except ObjectDoesNotExist:
                # User has not applied for it, so apply them if they're eligible
                # and the program has auto-apply enabled
                if user_eligible and program.enable_autoapply:
                    IQProgram.objects.create(
                        user_id=usr.id,
                        program_id=program.id,
                    )
                    update_counts['applied_users'] += 1
                    # log.debug(
                    #     f"User auto-applied for '{program.program_name}' IQ program",
                    #     function='finalize_application',
                    #     user_id=user.id,
                    # )

            else:
                # User has applied, so determine new eligibility

                # If user is enrolled, ignore the user regardless of eligibility
                if applied_program.is_enrolled:
                    update_counts['ignored_users'] += 1
                    continue

                # User isn't enrolled, so remove the programs if the user isn't
                # eligible
                if not user_eligible:
                    applied_program.delete()
                    update_counts['removed_users'] += 1

    return update_counts
