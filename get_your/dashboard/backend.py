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

import logging
from enum import Enum

import pendulum
from django.contrib.auth import get_user_model
from django.shortcuts import reverse

from app.constants import enable_calendar_year_renewal
from app.models import IQProgram
from monitor.wrappers import LoggerWrapper
from ref.models import IQProgram as IQProgramRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()


class QualificationStatus(Enum):
    NOTQUALIFIED = "NOT QUALIFIED"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"


def build_qualification_button(users_enrollment_status):
    # Create a dictionary to hold the button information
    return {
        "PENDING": {"text": "Applied", "color": "green", "textColor": "white"},
        "ACTIVE": {"text": "Enrolled!", "color": "blue", "textColor": "white"},
        "RENEWAL": {"text": "Renew", "color": "orange", "textColor": "white"},
        "": {"text": "Apply Now", "color": "", "textColor": ""},
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
        if (
            program.is_enrolled
            and needs_renewal
            and program.renewal_interval_year is not None
        ):
            return "RENEWAL"
        if program.is_enrolled:
            return "ACTIVE"

    except Exception:
        return ""


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
            "program",
        )
        .filter(
            user_id=user_id,
            program__is_active=True,
        )
        .order_by("program__id"),
    )

    # Collapse any programs the user has already applied for into all programs
    # they are eligible for. The starting point is 'eligible programs' as
    # IQProgramRef objects, then any program the user is in gets converted to an
    # IQProgram object for later identification
    programs = []
    for prg in eligible_iq_programs:
        # Append the matching users_iq_programs element to programs if it
        # exists; else append the eligible_iq_programs element
        try:
            iq_program = next(x for x in users_iq_programs if x.program_id == prg.id)
        except StopIteration:
            programs.append(prg)
        else:
            programs.append(iq_program)

    # Determine if the user needs renewal for *any* program, and set as a user-
    # level 'needs renewal'
    needs_renewal = check_if_user_needs_to_renew(user_id)

    for program in programs:
        program.renewal_interval_year = (
            program.program.renewal_interval_year
            if hasattr(program, "program")
            else program.renewal_interval_year
        )
        status_for_user = map_iq_enrollment_status(program, needs_renewal=needs_renewal)
        program.button = build_qualification_button(status_for_user)
        program.status_for_user = status_for_user
        program.quick_apply_link = reverse(
            "dashboard:quick_apply",
            kwargs={
                "iq_program": program.program.program_name
                if hasattr(program, "program")
                else program.program_name,
            },
        )
        program.title = (
            program.program.friendly_name
            if hasattr(program, "program")
            else program.friendly_name
        )
        program.subtitle = (
            program.program.friendly_category
            if hasattr(program, "program")
            else program.friendly_category
        )
        program.description = (
            program.program.friendly_description
            if hasattr(program, "program")
            else program.friendly_description
        )
        program.supplemental_info = (
            program.program.friendly_supplemental_info
            if hasattr(program, "program")
            else program.friendly_supplemental_info
        )
        program.eligibility_review_status = (
            "We are reviewing your application! Stay tuned here and check your email for updates."
            if status_for_user == "PENDING"
            else "",
        )
        program.eligibility_review_time_period = (
            program.program.friendly_eligibility_review_period
            if hasattr(program, "program")
            else program.friendly_eligibility_review_period
        )
        program.learn_more_link = (
            program.program.learn_more_link
            if hasattr(program, "program")
            else program.learn_more_link
        )
        program.enable_autoapply = (
            program.program.enable_autoapply
            if hasattr(program, "program")
            else program.enable_autoapply
        )
        program.ami_threshold = (
            program.program.ami_threshold
            if hasattr(program, "program")
            else program.ami_threshold
        )
        program.id = program.program.id if hasattr(program, "program") else program.id
    return programs


def check_if_user_needs_to_renew(user_id):
    """Checks if the user needs to renew their application
    Args:
        user_id (int): The ID (primary key) of the User object
    Returns:
        bool: True if the user needs to renew their application, False otherwise
    """
    user_profile = User.objects.get(id=user_id)

    # Get the highest frequency renewal_interval_year from active IQProgramRef
    # values and filter out any null renewal_interval_year
    highest_freq_program = (
        IQProgramRef.objects.filter(
            is_active=True,
            renewal_interval_year__isnull=False,
        )
        .order_by("renewal_interval_year")
        .first()
    )

    # If there are no programs without lifetime enrollment (e.g. without
    # non-null renewal_interval_year), always return False for needs_renewal
    if highest_freq_program is None:
        return False

    highest_freq_renewal_interval = highest_freq_program.renewal_interval_year

    # The highest_freq_renewal_interval is measured in years. We need to check
    # if the user's next renewal date is greater than or equal to the current
    # date.
    needs_renewal = (
        pendulum.instance(user_profile.last_completed_at).add(
            years=highest_freq_renewal_interval,
        )
        <= pendulum.now()
    )

    return needs_renewal


def enable_renew_now(user_id):
    """
    Enable the 'Renew Now' button on the dashboard pages
    """
    # Get the year from the last_completed_at of the user
    user_profile = User.objects.get(id=user_id)
    last_completed_at = user_profile.last_completed_at.year

    # Get the highest frequency renewal_interval_year from the IQProgramRef
    # table and filter out any null renewal_interval_year
    highest_freq_program = (
        IQProgramRef.objects.filter(renewal_interval_year__isnull=False)
        .order_by("renewal_interval_year")
        .first()
    )

    # If there are no programs without lifetime enrollment (e.g. without
    # non-null renewal_interval_year), always return False
    if highest_freq_program is None:
        return False

    if (
        enable_calendar_year_renewal
        and pendulum.now().year
        == last_completed_at + highest_freq_program.renewal_interval_year
    ):
        return True
    return False
