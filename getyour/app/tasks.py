from app.backend import broadcast_renewal_email, check_if_user_needs_to_renew
from app.models import User
from app.constants import notification_buffer_month
from logger.wrappers import LoggerWrapper

from django_q.tasks import async_task
import logging
import pendulum


def run_renewal_task():
    """
    Run the task to send an automated 'renewal required' email to each affected
    user.
    
    """

    # Initialize logger
    log = LoggerWrapper(logging.getLogger(__name__))

    log.debug(
        "Entering function",
        function='run_renewal_task',
    )

    # For every user in the database that isn't archived or has a NULL
    # last_completed_at, run the send_renewal_email task (asynchronously)
    for user in User.objects.filter(
        is_archived=False,
        last_completed_at__isnull=False,
    ):
        async_task(send_renewal_email, user)


def send_renewal_email(user):
    """
    Determine if the user
    a) needs to renew and
    b) hasn't been notified within the buffer period
    
    and kick off the 'renewal required' email.

    """

    # Initialize logger (needs to be done within the async task)
    log = LoggerWrapper(logging.getLogger(__name__))

    # Check if user needs to renew their application
    needs_renewal = check_if_user_needs_to_renew(user.id)

    # If they need to renew and if they have been notified within the
    # notification buffer period, send them a renewal email.
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
            log.info(
                "User needs renewal; sending notification",
                function='send_renewal_email',
                user_id=user.id,
            )
            
            # Note that SendGrid doesn't have rate limits for 'send' operations
            # in the v3 API (used here), so this needs no rate consideration
            status_code = broadcast_renewal_email(user.email)

            # Now update the user's last_action_notification_at
            # field to the current time if status_code is '202 Accepted' (see
            # https://docs.sendgrid.com/ui/account-and-settings/api-keys#testing-an-api-key
            # for the closest documentation I could find)
            if status_code == 202:
                log.debug(
                    f"SendGrid call successful. last_action_notification_at updating from '{user.last_action_notification_at}'",
                    function='send_renewal_email',
                    user_id=user.id,
                )
                user.last_action_notification_at = pendulum.now()
                user.save()
        else:
            log.debug(
                "User needs renewal but has recently been notified",
                function='send_renewal_email',
                user_id=user.id,
            )

            # TODO: Discuss archiving users that haven't renewed and have
            # exceeded the `notification_buffer_month` notification window

    else:
        log.debug(
            "User does not need renewal",
            function='send_renewal_email',
            user_id=user.id,
        )
