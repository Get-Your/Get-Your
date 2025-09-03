"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

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

import re

from django.conf import settings


def global_template_variables(request):
    """These are context variables that are available to all templates"""

    # Set the contact number to display on the site. This is the prettified Twilio
    # number set in the config vars
    parsed_number = re.match(
        r"\+?\d?(\d{3})(\d{3})(\d{4})$",
        settings.TWILIO_AUTOMATED_SMS_NUMBER,
    )
    contact_number = "({prs[0]}) {prs[1]}-{prs[2]}".format(
        prs=parsed_number.groups(),
    )

    data = {
        "is_prod": settings.IS_PROD,
        "code_version": settings.CODE_VERSION,
        "contact_email": settings.CONTACT_EMAIL,
        "contact_number": contact_number,
    }

    return data
