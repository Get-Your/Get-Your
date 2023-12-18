from app.backend import broadcast_renewal_email, check_if_user_needs_to_renew
from app.models import User

def send_renewal_email():
    # For every user in the database, check if they
    # need to renew their application
    for user in User.objects.all():
        needs_renewal = check_if_user_needs_to_renew(user.id)
        if needs_renewal:
            broadcast_renewal_email(user.email)
    