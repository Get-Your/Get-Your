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
from django.db.models.signals import pre_save
from django.core.serializers.json import DjangoJSONEncoder
from django.dispatch import receiver
from app.models import Household, HouseholdHist, User, UserHist, Address, AddressHist
from app.backend import changed_modelfields_to_dict


@receiver(pre_save, sender=Household)
def household_pre_save(sender, instance, **kwargs):
    # Run historical save if update or renewal mode
    if instance.update_mode or instance.renewal_mode:
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
                            ), cls=DjangoJSONEncoder
                        )
                    )
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
            else:
                # If renewal_mode, set is_updated regardless of values have changed
                instance.is_updated = instance.renewal_mode


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # The user object gets saved at times other than update_mode (such as
    # login), so check for the appropriate var before attempting history save
    if instance.update_mode or instance.renewal_mode:
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
                            ), cls=DjangoJSONEncoder
                        )
                    )
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
            else:
                # If renewal_mode, set is_updated regardless of values have changed
                instance.is_updated = instance.renewal_mode


@receiver(pre_save, sender=Address)
def address_pre_save(sender, instance, **kwargs):
    # Run historical save if update or renewal mode
    if instance.update_mode or instance.renewal_mode:
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
                            ), cls=DjangoJSONEncoder
                        )
                    )
                )

        except Address.DoesNotExist:
            # No historical data to use for the update
            pass

        else:
            # Save or perform operations with the original instance
            address_history.save()

        # Ensure ``is_..._updated`` is set (regardless whether any field changes)
        # Eligibility address changes only take place in renewal mode
        # Mailing address changes can take place in either mode
        instance.is_eligibility_address_updated = instance.renewal_mode
        instance.is_mailing_address_updated = instance.update_mode or instance.renewal_mode
