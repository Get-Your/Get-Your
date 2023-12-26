from app.backend import broadcast_renewal_email, check_if_user_needs_to_renew
from app.models import User

def send_renewal_email():
    # For every user in the database that isn't archived, check if they
    # need to renew their application
    for user in User.objects.filter(is_archived=False):
        needs_renewal = check_if_user_needs_to_renew(user.id)
        # Check if the user needs to renew and if they have been notified in the last
        # 30 days. If they haven't been notified, send them a renewal email.
        if needs_renewal:
            # Check if the user has been notified in the last 30 days
            days_since_last_notification = (datetime.now() - user.last_action_notification_at).days
            if days_since_last_notification > 30:
                broadcast_renewal_email(user.email)
                # Now update the user's last_action_notification_at
                # field to the current time
                user.last_action_notification_at = datetime.now()
                user.save()
            else:
                # TODO: Archive users that haven't renewed and have exceeded the 30 day
                # notification window
                continue
    