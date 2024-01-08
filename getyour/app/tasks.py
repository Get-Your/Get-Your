from app.backend import broadcast_renewal_email, check_if_user_needs_to_renew
from app.models import User
from app.constants import notification_buffer_month
from log.wrappers import LoggerWrapper

import logging
import pendulum


def send_renewal_email():
    # Initialize logger
    logger = LoggerWrapper(logging.getLogger(__name__))

    logger.debug(
        "Entering function",
        function='send_renewal_email',
    )

    # For every user in the database that isn't archived, check if they
    # need to renew their application
    for user in User.objects.filter(is_archived=False):
        needs_renewal = check_if_user_needs_to_renew(user.id)

        # Check if the user needs to renew and if they have been notified within
        # the notification buffer period. If they haven't been notified, send
        # them a renewal email.
        if needs_renewal:
            # Check if the user has been notified within the specified period
            # Note that `.months` specifies number of months within a year,
            # where `in_months()` (used here) specifies overall number of months
            # (e.g. period.months + period.years*12 = period.in_months())
            months_since_last_notification = (pendulum.now() - user.last_action_notification_at).in_months()
            if months_since_last_notification > notification_buffer_month:
                logger.info(
                    "User needs renewal; sending notification",
                    function='send_renewal_email',
                    user_id=user.id,
                )
                
                broadcast_renewal_email(user.email)

                # Now update the user's last_action_notification_at
                # field to the current time
                user.last_action_notification_at = pendulum.now()
                user.save()
            else:
                logger.debug(
                    "User needs renewal but has recently been notified",
                    function='send_renewal_email',
                    user_id=user.id,
                )

                # TODO: Discuss archiving users that haven't renewed and have
                # exceeded the 30 day notification window
