import pendulum
from django.contrib.auth import get_user_model

from app.backend import check_if_user_needs_to_renew
from app.constants import notification_buffer_month

# Get the user model
User = get_user_model()
# For every user in the database that isn't archived or has a NULL
# last_completed_at, check if they need to renew their application
notificationList = []
nonNotifyList = []
for user in User.objects.filter(
    is_archived=False,
    last_completed_at__isnull=False,
):
    needs_renewal = check_if_user_needs_to_renew(user.id)
    # Check if the user needs to renew and if they have been notified within
    # the notification buffer period. If they haven't been notified, send
    # them a renewal email.
    if needs_renewal:
        # Check if the user has been notified within the specified period
        # Note that the user will be notified each `notification_buffer_month`
        # months
        # `.months` specifies number of months within a year,
        # where `in_months()` (used here) specifies overall number of months
        # (e.g. period.months + period.years*12 = period.in_months())
        months_since_last_notification = (
            pendulum.now() - user.last_action_notification_at
        ).in_months()
        if months_since_last_notification > notification_buffer_month:
            # print(
            #     f"User {user.id} needs renewal; notification would be sent",
            # )
            notificationList.append(user.id)
        else:
            # print(
            #     f"User {user.id} needs renewal but has recently been notified",
            # )
            nonNotifyList.append(user.id)
