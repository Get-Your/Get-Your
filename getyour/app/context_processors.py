import re

from django.conf import settings


def global_template_variables(request):
    """These are context variables that are available to all templates"""

    # Set the contact number to display on the site. This is the prettified Twilio
    # number set in the config vars
    parsed_number = re.match(
        r'\+?\d?(\d{3})(\d{3})(\d{4})$',
        settings.TWILIO_NUMBER,
    )
    contact_number = "({prs[0]}) {prs[1]}-{prs[2]}".format(
        prs=parsed_number.groups()
    )

    data = {
        'is_prod': settings.IS_PROD,
        'code_version': settings.CODE_VERSION,
        'contact_email': settings.CONTACT_EMAIL,
        'contact_number': contact_number,
    }

    return data
