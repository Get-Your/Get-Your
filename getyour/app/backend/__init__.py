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
from enum import Enum
from itertools import chain
import logging
import pendulum
import httpagentparser

from twilio.rest import Client
from sendgrid.helpers.mail import Mail
from sendgrid import SendGridAPIClient

from django.shortcuts import reverse
from django.contrib.auth.backends import UserModel
from django.contrib.auth import login as django_auth_login
from django.conf import settings
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from django.core.serializers.json import DjangoJSONEncoder
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
from logger.wrappers import LoggerWrapper

from python_http_client.exceptions import HTTPError as SendGridHTTPError
from twilio.base.exceptions import TwilioRestException
from app.constants import enable_calendar_year_renewal, application_pages


# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


form_page_number = 6


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


def broadcast_email(email):
    message = Mail(
        from_email='getfoco@fcgov.com',
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
        from_email='getfoco@fcgov.com',
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
        from_email='getfoco@fcgov.com',
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
    # Get the IQ programs that a user has already applied to
    users_iq_programs = list(IQProgram.objects.select_related(
        'program').filter(user_id=user_id))

    # Filter only programs that are active
    users_iq_programs = [x for x in users_iq_programs if x.program.is_active]

    # Get the IQ programs a user is eligible for
    users_iq_programs_ids = [
        program.program_id for program in users_iq_programs]
    active_iq_programs = list(IQProgramRD.objects.filter(
        (Q(is_active=True) & Q(ami_threshold__gte=users_income_as_fraction_of_ami) & ~Q(
            id__in=users_iq_programs_ids))
    ))

    # Filter out the active programs that the user is not geographically eligible for.
    # If the IQ program's req_is_city_covered is true, then check to make sure
    # the user's eligibility address is_city_covered.
    active_iq_programs = [
        program for program in active_iq_programs if not (program.req_is_city_covered and not users_eligiblity_address.is_city_covered)]

    # Gather list of active programs
    programs = list(chain(users_iq_programs, active_iq_programs))
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
        print()
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
