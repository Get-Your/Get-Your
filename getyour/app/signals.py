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
from app.backend import model_to_dict


@receiver(pre_save, sender=Household)
def household_pre_save(sender, instance, **kwargs):
    try:
        # Save the user's current household data to the database in the
        # household history table.
        users_household = Household.objects.get(user_id=instance.user_id)
        household_history = HouseholdHist.objects.create(
            user=instance.user,
            # Convert the household object to a dictionary and then to a JSON string
            # and set it to the historical_values field
            historical_values=json.loads(json.dumps(
                model_to_dict(users_household), cls=DjangoJSONEncoder))
        )
    except Household.DoesNotExist:
        users_household = None

    if users_household:
        # Save or perform operations with the original instance
        household_history.save()


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    try:
        # Save the user's current user data to the database in the
        # user history table.
        users_user = User.objects.get(id=instance.id)
        user_history = UserHist.objects.create(
            user=instance,
            # Convert the user object to a dictionary and then to a JSON string
            # and set it to the historical_values field
            historical_values=json.loads(json.dumps(
                model_to_dict(users_user, include_fk=True), cls=DjangoJSONEncoder))
        )
    except User.DoesNotExist:
        users_user = None

    if users_user:
        # Save or perform operations with the original instance
        user_history.save()


@receiver(pre_save, sender=Address)
def address_pre_save(sender, instance, **kwargs):
    try:
        # Save the user's current address data to the database in the
        # address history table. Since the AddressRD data don't change, only
        # the Address data need to be preserved.
        users_address = Address.objects.get(user_id=instance.user_id)
        address_history = AddressHist.objects.create(
            user=instance.user,
            # Convert the user object to a dictionary and then to a JSON string
            # and set it to the historical_values field
            historical_values=json.loads(json.dumps(
                model_to_dict(users_address, include_fk=True), cls=DjangoJSONEncoder))
        )
    except Address.DoesNotExist:
        users_address = None

    if users_address:
        # Save or perform operations with the original instance
        address_history.save()