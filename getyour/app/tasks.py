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

from sendgrid.helpers.mail import Mail
from sendgrid import SendGridAPIClient

from python_http_client.exceptions import (
    HTTPError as SendGridHTTPError,
    BadRequestsError as SendGridBadRequest,
)

from django.conf import settings
from django.core.cache import cache
from django_q.tasks import async_task

from app.backend import broadcast_renewal_email, check_if_user_needs_to_renew
from app.models import User
from app.constants import notification_buffer_month
from logger.wrappers import LoggerWrapper


def populate_cache_task():
    async_task(populate_redis_cache)


def populate_redis_cache():
    users = User.objects.all()
    for user in users:
        cache_key = f"user_last_notified_{user.id}"

        # Check if user needs to renew their application. We don't want to
        # cache users that don't need application renewals
        needs_renewal = check_if_user_needs_to_renew(user.id)

        if needs_renewal and user.last_action_notification_at:
            cache.set(cache_key, str(user.last_action_notification_at), timeout=3600 * 24 * 30)


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
        cache_key = f"user_last_notified_{user.id}"
        last_notified = cache.get(cache_key)
        should_enqueue = (
            last_notified is None or 
            (pendulum.now() - pendulum.parse(last_notified)).in_months() > notification_buffer_month
        )
        
        if should_enqueue:
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
    cache_key = f"user_last_notified_{user.id}"

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
        last_notified = cache.get(cache_key)
        should_notify = (
            last_notified is None or 
            (pendulum.now() - pendulum.parse(last_notified)).in_months() > notification_buffer_month
        )
        if should_notify:
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
                cache.set(cache_key, str(pendulum.now()), timeout=3600 * 24 * 30 * notification_buffer_month)
            else:
                log.debug(
                    f"SendGrid call failed. SendGrid status_code: '{status_code}'",
                    function='send_renewal_email',
                    user_id=user.id,
                )
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


def send_generic_email(template_str, *args):
    """
    Send a generic email to any number of recipients. This allows a scheduled
    email to be sent via the email service without code changes, by just adding
    it to the Django-Q schedule.

    This is 'generic' because it must follow these rules:
    - The email template cannot be passed any parameters
    - There are no CC addresses; all users (in the *args parameter) are sent
    the same email, each with their own version.

    Parameters
    ----------
    template_str : str
        Either the name of the email template to use (specified in the .env file
        with a corresponding template ID) or the template ID itself. The name
        will be checked first.
    *args : str
        Each arg is the email address of a recipient. Each recipient will be
        sent the email specified by ``template_str`` (these will not be sent
        as a single bulk email).

    Returns
    -------
    None

    """

    # Initialize logger
    log = LoggerWrapper(logging.getLogger(__name__))

    log.info(
        f"Entering function using template '{template_str}'",
        function='send_generic_email',
    )

    # Determine if the template name or ID is to be used
    try:
        template_id = getattr(settings, template_str)
    except AttributeError:
        template_id = template_str
        log.info(
            f"'{template_str}' is not a known template name; attempting to use as ID",
            function='send_generic_email',
        )
    else:
        log.info(
            f"'{template_str}' is a known template name",
            function='send_generic_email',
        )

    # Loop through each value in *args to send the email. Since the email itself
    # is handled by the email service, this is done synchronously for simplicity
    try:
        for eml in args:
            log.debug(
                f"Attempting email to {eml}",
                function='send_generic_email',
            )
            
            message = Mail(
                from_email='getfoco@fcgov.com',
                to_emails=eml)

            message.template_id = template_id
            try:
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                _ = sg.send(message)

            except SendGridBadRequest:
                log.exception(
                    f"Template likely does not exist; exiting function",
                    function='send_generic_email',
                )
                # exit the loop if this exception is raised
                break

            except SendGridHTTPError as e:
                log.exception(
                    f"Sendgrid returned: {e}",
                    function='send_generic_email',
                )
        
    except Exception as e:
        log.exception(
            "General exception raised; exiting function",
            function='send_generic_email',
        )
        raise
