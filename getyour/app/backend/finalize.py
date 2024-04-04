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
import logging
import pendulum
from decimal import Decimal

from django.db.models import Q
from app.models import (
    EligibilityProgram,
    IQProgramRD,
    IQProgram,
    User,
    Household,
    AddressRD,
)
from app.backend import get_users_iq_programs, get_eligible_iq_programs

from logger.wrappers import LoggerWrapper


# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def finalize_address(instance, is_in_gma, has_connexion):
    """ Finalize the address, given inputs calculated earlier. """

    # Record the service area and Connexion status
    instance.is_in_gma = is_in_gma
    instance.is_city_covered = is_in_gma
    instance.has_connexion = has_connexion

    # Final step: mark the address record as 'verified' and save
    instance.is_verified = True
    instance.save()


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


def remove_ineligible_programs(
        user,
        income_override: Decimal = None,
    ):
    """
    Remove programs that a user no longer qualifies for, based on application
    updates made after the user selected their programs.

    A use-case for this is when a user's documentation is changed from a 30% AMI
    eligibility program to a 60% AMI program via the admin panel.

    ``income_override`` will be used instead of ``income_as_a_fraction_of_ami``
    in get_eligible_iq_programs to test changes to the user's Household.
    ``income_override`` should be a Decimal() type.

    """

    # Get the user's eligibility address
    eligibility_address = AddressRD.objects.filter(
        id=user.address.eligibility_address_id
    ).first()

    # Get the user's current programs
    users_iq_programs = IQProgram.objects.filter(user_id=user.id)

    # Get the programs the user is eligible for
    eligible_programs = get_eligible_iq_programs(
        user,
        eligibility_address,
        income_override=income_override,
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
    for program in ineligible_current_programs:
        program.delete()
        msg.append(f"User was removed from {program.program.program_name}")

    return '; '.join(msg)
