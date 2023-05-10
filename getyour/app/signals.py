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
