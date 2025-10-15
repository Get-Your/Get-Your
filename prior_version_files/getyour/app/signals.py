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

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import Signal, receiver

from app.backend import changed_modelfields_to_dict
from app.models import (
    Address,
    AddressHist,
    EligibilityProgram,
    EligibilityProgramHist,
    Household,
    HouseholdHist,
    HouseholdMembers,
    HouseholdMembersHist,
    IQProgram,
    IQProgramHist,
    User,
    UserHist,
)
from app.tasks import populate_cache_task

# Defines a custom signal for us to listen for
populate_cache = Signal()


@receiver(pre_save, sender=Household)
def household_pre_save(sender, instance, **kwargs):
    # Run historical save if update or renewal mode
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields that have been updated in the
            # user's household data to the database in the householdhist table
            household_history = HouseholdHist(
                user=instance.user,
                # Convert the updated household objects to a dictionary and then to
                # a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except Household.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if household_history.historical_values != {}:
                household_history.save()
                # Set is_updated if any values have changed
                instance.is_updated = True


@receiver(pre_save, sender=HouseholdMembers)
def householdmembers_pre_save(sender, instance, **kwargs):
    # Run historical save if update or renewal mode
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields that have been updated in the
            # user's householdmembers data to the database in the
            # householdmembershist table
            householdmembers_history = HouseholdMembersHist(
                user=instance.user,
                # Convert the updated household objects to a dictionary and then to
                # a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except HouseholdMembers.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if householdmembers_history.historical_values != {}:
                householdmembers_history.save()
                # Set is_updated if any values have changed
                instance.is_updated = True


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # The user object gets saved at times other than update_mode (such as
    # login), so check for the appropriate var before attempting history save
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields that have been updated in the
            # user's account data to the database in the userhist table
            user_history = UserHist(
                user=instance,
                # Convert the updated user objects to a dictionary and then to
                # a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except User.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if user_history.historical_values != {}:
                user_history.save()
                # Set is_updated if any values have changed
                instance.is_updated = True


@receiver(pre_save, sender=Address)
def address_pre_save(sender, instance, **kwargs):
    # Run historical save if update or renewal mode
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields that have been updated in the
            # user's address data to the database in the addresshist table. Since
            # the AddressRD data don't change, only the Address data need to be
            # preserved
            address_history = AddressHist(
                user=instance.user,
                # Convert the updated address objects to a dictionary and then to
                # a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except Address.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if address_history.historical_values != {}:
                address_history.save()
                # Set is_updated *only if mailing address is included* in the
                # updated values
                if "mailing_address_id" in address_history.historical_values.keys():
                    instance.is_updated = True


# Since this table is only affected by new or renewal applications, use
# pre_delete instead of pre_save
@receiver(pre_delete, sender=IQProgram)
def iqprogram_pre_delete(sender, instance, **kwargs):
    # Run historical save if update or renewal mode (although update_mode
    # shouldn't trigger this function)
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields to be deleted from the
            # user's iq program data to the database in the
            # iqprogramhist table
            iqprogram_history = IQProgramHist(
                user=instance.user,
                # Convert the iqprogram objects to a dictionary and then to
                # a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                            pre_delete=True,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except IQProgram.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if iqprogram_history.historical_values != {}:
                iqprogram_history.save()
                # Set is_updated if any values have changed
                instance.is_updated = True


# Since this table is only affected by new or renewal applications, use
# pre_delete instead of pre_save
@receiver(pre_delete, sender=EligibilityProgram)
def eligiblity_program_pre_delete(sender, instance, **kwargs):
    # Run historical save if update or renewal mode (although update_mode
    # shouldn't trigger this function)
    if instance.update_mode or instance.renewal_mode or instance.admin_mode:
        try:
            # Save the previous values of the fields to be deleted from the
            # user's eligibility program data to the database in the
            # eligibilityprogramhist table
            eligiblity_program_history = EligibilityProgramHist(
                user=instance.user,
                # Convert the eligibilityprogram objects to a dictionary and
                # then to a JSON string and set it to the historical_values field
                historical_values=json.loads(
                    json.dumps(
                        changed_modelfields_to_dict(
                            sender.objects.get(pk=instance.pk),
                            instance,
                            pre_delete=True,
                        ),
                        cls=DjangoJSONEncoder,
                    )
                ),
            )

        except EligibilityProgram.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance if any field
            # has changed
            if eligiblity_program_history.historical_values != {}:
                eligiblity_program_history.save()
                # Set is_updated if any values have changed
                instance.is_updated = True


@receiver(populate_cache)
def trigger_cache_population(sender, **kwargs):
    populate_cache_task()
