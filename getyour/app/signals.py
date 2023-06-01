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
from app.models import Household, HouseholdHist
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
            # and set it to the historical_household field
            historical_values=json.loads(json.dumps(
                model_to_dict(users_household), cls=DjangoJSONEncoder))
        )
    except Household.DoesNotExist:
        users_household = None

    if users_household:
        # Save or perform operations with the original instance
        household_history.save()
