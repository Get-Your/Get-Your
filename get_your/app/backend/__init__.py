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

import datetime
import json
import logging

import httpagentparser
import magic
import pendulum
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_auth_login
from django.contrib.auth.backends import UserModel
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import UploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from django.db.models.query import QuerySet
from phonenumber_field.phonenumber import PhoneNumber
from python_http_client.exceptions import HTTPError as SendGridHTTPError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.constants import application_pages
from app.constants import supported_content_types
from app.models import EligibilityProgram
from app.models import Household
from app.models import HouseholdMembers
from app.models import IQProgram
from dashboard.backend import get_users_iq_programs
from monitor.wrappers import LoggerWrapper
from ref.models import Address as AddressRef
from ref.models import IQProgram as IQProgramRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()


form_page_number = 6


def broadcast_sms(phone_Number):
    message_to_broadcast = "Thank you for creating an account with Get FoCo! Be sure to review the programs you qualify for on your dashboard and click on Apply Now to finish the application process!"
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        message_instance = client.messages.create(
            to=phone_Number,
            from_=settings.TWILIO_AUTOMATED_SMS_NUMBER,
            body=message_to_broadcast,
        )
    except TwilioRestException as e:
        log.exception(e, function="broadcast_sms")


def broadcast_email(email):
    message = Mail(from_email=settings.CONTACT_EMAIL, to_emails=email)

    message.template_id = settings.WELCOME_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned HTTP {response.status_code}",
            function="broadcast_email",
        )
    except Exception as e:
        log.exception(e, function="broadcast_email")


def broadcast_email_pw_reset(email, content):
    message = Mail(
        subject="Password Reset Requested",
        from_email=settings.CONTACT_EMAIL,
        to_emails=email,
    )
    message.dynamic_template_data = {
        "subject": "Password Reset Requested",
        "html_content": content,
    }
    message.template_id = settings.PW_RESET_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned HTTP {response.status_code}",
            function="broadcast_email_pw_reset",
        )
    except Exception as e:
        log.exception(
            e,
            function="broadcast_email_pw_reset",
        )


def broadcast_renewal_email(email):
    message = Mail(from_email=settings.CONTACT_EMAIL, to_emails=email)

    message.template_id = settings.RENEWAL_EMAIL_TEMPLATE
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        log.info(
            f"Sendgrid returned: HTTP {response.status_code}",
            function="broadcast_renewal_email",
        )

    except SendGridHTTPError as response:
        log.exception(
            f"Sendgrid returned: {response}",
            function="broadcast_renewal_email",
        )

    return response.status_code


def changed_modelfields_to_dict(
    previous_instance,
    current_instance,
    pre_delete=False,
):
    """
    Convert a model object to a dictionary. This is used specifically for
    writing to history tables.

    If a property is a datetime object, it will be converted to a string. If
    there is a nested model, it will be excluded from the dictionary. If
    pre_delete is True, the previous instance is returned as a dictionary.

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
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(value, PhoneNumber):
                        value = value.as_e164
                    model_dict[field.name] = value

            except AttributeError:
                pass
    else:
        # Compare the current instance with the previous instance
        for field in current_instance._meta.fields:
            field_name = field.name
            if getattr(current_instance, field_name) != getattr(
                previous_instance,
                field_name,
            ):
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
                            value = value.strftime("%Y-%m-%d %H:%M:%S")
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
        if k != "csrfmiddlewaretoken"
    }

    # Create a list of dictionaries with 'name' and 'birthdate' keys
    household_members = [
        {
            "name": household_members_data["name"][i],
            "birthdate": household_members_data["birthdate"][i],
            "identification_path": file_paths[i],
        }
        for i in range(len(household_members_data["name"]))
    ]

    household_info = json.loads(
        json.dumps({"persons_in_household": household_members}, cls=DjangoJSONEncoder),
    )
    return household_info


def login(request, user):
    django_auth_login(request, user)

    # Try to log user agent data
    try:
        log.info(
            "User logged in; agent is {}".format(
                httpagentparser.simple_detect(request.META["HTTP_USER_AGENT"]),
            ),
            function="login",
            user_id=request.user.id,
        )
    except Exception:
        log.exception(
            "HTTP agent parsing failed!",
            function="login",
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

        if HouseholdMembers.objects.all().filter(user_id=request.user.id).exists():
            pass
        else:
            return "app:household_members"

        # Check to see if the user has selected any eligibility programs
        if request.user.eligibility_files.count():
            pass
        else:
            return "app:programs"

        users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
            request,
        )
        if users_programs_without_uploads.count():
            return "app:files"

        return "app:dashboard"
    return "app:account"


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
    income_eligible_iq_programs = IQProgramRef.objects.filter(
        is_active=True,
        # If income_as_fraction_of_ami is None, set to 100% to exclude all programs
        ami_threshold__gte=user.household.income_as_fraction_of_ami or 1,
    ).order_by("id")

    # Filter programs further based on address requirements

    # Gather all `requires_` fields in the IQProgramRef model along with their
    # corresponding AddressRef Boolean
    req_fields = get_iqprogram_requires_fields()

    # For each program, take (<address Boolean> or not <requires_>) for all
    # `requires_` fields (see ARCHITECTURE.md for details), and AND them
    # together (via all())
    eligible_iq_programs = [
        prog
        for prog in income_eligible_iq_programs
        if all(
            (getattr(eligibility_address, cor) or not getattr(prog, req))
            for req, cor in req_fields
        )
    ]

    return eligible_iq_programs


def get_in_progress_eligiblity_file_uploads(request):
    """Returns a list of eligibility programs that are in progress. This is just a shim for now
    and will eventually be replaced by a call to the database through Django's ORM
    Returns:
        list: List of eligibility programs
    """
    users_in_progress_file_uploads = (
        EligibilityProgram.objects.filter(
            Q(user_id=request.user.id) & Q(document_path=""),
        )
        .select_related("program")
        .values("id", "program__id", "program__friendly_name")
    )
    return users_in_progress_file_uploads


def save_renewal_action(request_or_user, action, status="completed", data={}):
    """Saves a renewal action to the database
    Args:
        request_or_user (HttpRequest or User object): The request object or User
        action (str): The action to save
    """
    if isinstance(request_or_user, http.HttpRequest):
        user = UserModel.objects.get(id=request_or_user.user.id)
    else:
        user = request_or_user

    if hasattr(user, "last_renewal_action"):
        last_renewal_action = (
            user.last_renewal_action if user.last_renewal_action else {}
        )

        # Check if the action exists in the last renewal action
        if action in last_renewal_action:
            last_renewal_action[action] = {"status": status, "data": data}
        else:
            last_renewal_action[action] = {"status": status, "data": data}

        user.last_renewal_action = json.loads(
            json.dumps(last_renewal_action, cls=DjangoJSONEncoder),
        )
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
        function="finalize_application",
        user_id=user.id,
    )

    # Get all of the user's eligiblity programs and find the one with the lowest
    # 'ami_threshold' value which can be found in the related
    # eligiblityprogramrd table
    lowest_ami = (
        EligibilityProgram.objects.filter(Q(user_id=user.id))
        .select_related("program")
        .values("program__ami_threshold")
        .order_by("program__ami_threshold")
        .first()
    )

    # Now save the value of the ami_threshold to the user's household
    household = Household.objects.get(Q(user_id=user.id))
    household.income_as_fraction_of_ami = lowest_ami["program__ami_threshold"]

    if renewal_mode:
        household.is_income_verified = False
        household.save()

        # Set the user's last_completed_date to now, as well as set the user's
        # last_renewal_action to null
        if update_user:
            user = User.objects.get(id=user.id)
            # user.renewal_mode = True
            user.last_completed_at = pendulum.now()
            user.last_renewal_action = None
            user.save()

        # Get every IQ program for the user that have a renewal_interval_year
        # in the IQProgramRef table that is not null
        users_current_iq_programs = (
            IQProgram.objects.filter(Q(user_id=user.id))
            .select_related("program")
            .order_by("program__renewal_interval_year")
            .exclude(program__renewal_interval_year__isnull=True)
        )

        # For each element in users_current_iq_programs, delete the program.
        # Note that each element has a non-null renewal interval
        for program in users_current_iq_programs:
            # program.renewal_mode = True
            program.delete()

        # Get the user's eligibility address
        eligibility_address = AddressRef.objects.filter(
            id=user.address.eligibility_address_id,
        ).first()

        # Now get all of the IQ Programs for which the user is eligible
        users_iq_programs = get_users_iq_programs(
            user.id,
            lowest_ami["program__ami_threshold"],
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
            if program.id in [
                program.program.id for program in users_current_iq_programs
            ]:
                # Re-apply by creating the element
                IQProgram.objects.create(
                    user_id=user.id,
                    program_id=program.id,
                )

            # Otherwise, apply if the program has enable_autoapply set to True
            elif program.enable_autoapply:
                # Check if the user already has the program in the IQProgram table
                if not IQProgram.objects.filter(
                    Q(user_id=user.id) & Q(program_id=program.id),
                ).exists():
                    # If the user doesn't have the program in the IQProgram
                    # table, then create it
                    IQProgram.objects.create(
                        user_id=user.id,
                        program_id=program.id,
                    )

        # Return the target page and a dictionary of <session var>: <value>
        return (
            "dashboard:dashboard",
            {
                "app_renewed": True,
                "renewal_eligible": sorted(renewal_eligible),
                "renewal_ineligible": sorted(renewal_ineligible),
            },
        )

    household.save()

    if update_user:
        user.last_completed_at = pendulum.now()
        user.save()

    # Get the user's eligibility address
    eligibility_address = AddressRef.objects.filter(
        id=user.address.eligibility_address_id,
    ).first()

    # Now get all of the IQ Programs for which the user is eligible
    users_iq_programs = get_users_iq_programs(
        user.id,
        lowest_ami["program__ami_threshold"],
        eligibility_address,
    )
    # For every IQ program, check if the user should be automatically
    # enrolled in it if the program has enable_autoapply set to True
    for program in users_iq_programs:
        # program is an IQProgramRef object only if the user has not applied
        if isinstance(program, IQProgramRef) and program.enable_autoapply:
            IQProgram.objects.create(
                user_id=user.id,
                program_id=program.id,
            )
            log.debug(
                f"User auto-applied for '{program.program_name}' IQ program",
                function="finalize_application",
                user_id=user.id,
            )

    # Return the target page and an (empty) dictionary of <session var>: <value>
    return ("app:broadcast", {})


def get_iqprogram_requires_fields():
    """
    Gather all `requires_` fields in the IQProgramRef model along with their
    corresponding AddressRef Boolean.

    """
    field_prefix = "requires_"
    req_fields = [
        (x.name, x.name.replace(field_prefix, ""))
        for x in IQProgramRef._meta.fields
        if x.name.startswith(field_prefix)
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
        (x for x in supported_content_types if x in filetype.lower()),
        None,
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
        function="file_validation",
        user_id=user_id,
    )
    return (
        False,
        "File is not a valid type. Only these file types are supported: {}".format(
            ", ".join(supported_content_types),
        ),
    )


def remove_ineligible_programs_for_user(user_id, admin_mode=False):
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
    admin_mode : bool
        Whether this is being run in 'admin mode', in which the pre_delete
        signal is called.

    Returns
    -------
    str
        Returns the output message, with any compound messages joined by a
        semicolon.

    """

    # Get the user object (with updates that were presumably made just prior)
    user = User.objects.select_related("address").get(id=user_id)

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

    # Delete user from ineligible programs; return message describing the changes
    msg = []
    for prgrm in ineligible_current_programs:
        # Set admin_mode (where applicable) for proper signals functionality
        prgrm.admin_mode = admin_mode

        # Delete only if the user isn't enrolled
        if prgrm.is_enrolled:
            msg.append(
                f"{prgrm.program.program_name} not changed (user already enrolled)",
            )
        else:
            prgrm.delete()
            msg.append(f"User was removed from {prgrm.program.program_name}")

    return "; ".join(msg)


def update_users_for_program(
    *,  # force the following to be keyword-only parameters
    program: IQProgramRef,
    users: list | tuple | QuerySet,
    admin_mode: bool = False,
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
    program : IQProgramRef
        The ID of the specified program.
    users : Union[list, tuple, QuerySet]
        A list, tuple, or queryset of User objects to be updated for the
        specified program. This can be a queryset of all users, but will slow
        the updates.
    admin_mode : bool
        Whether this is being run in 'admin mode', in which the pre_delete
        signal is called.

    Returns
    -------
    dict
        Returns a dictionary of counts of removed users and ignored users.

    """
    # Initialize output counts
    update_counts = {
        "applied_users": 0,
        "removed_users": 0,
        "ignored_users": 0,
    }

    log.debug(
        f"{len(users)} user(s) to update for program '{program.program_name}'",
        function="update_users_for_program",
    )

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
                    update_counts["applied_users"] += 1

            else:
                # User has applied, so determine new eligibility

                # If user is enrolled, ignore the user regardless of eligibility
                if applied_program.is_enrolled:
                    update_counts["ignored_users"] += 1
                    continue

                # User isn't enrolled, so remove the programs if the user isn't
                # eligible
                if not user_eligible:
                    # Set admin_mode for proper signals functionality
                    applied_program.admin_mode = admin_mode

                    applied_program.delete()
                    update_counts["removed_users"] += 1

    return update_counts
