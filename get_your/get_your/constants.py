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

import logging

# Set the notification buffer to be used for reminders
notification_buffer_month = 1

# Enable Calendar Year Renewals
enable_calendar_year_renewal = True

# Set the specified app label and logging levels for use in the logging db
logger_app_labels = {"monitor"}
LOG_LEVELS = (
    (logging.NOTSET, "NotSet"),
    (logging.INFO, "Info"),
    (logging.WARNING, "Warning"),
    (logging.DEBUG, "Debug"),
    (logging.ERROR, "Error"),
    (logging.FATAL, "Fatal"),
)

# Define the content types supported by this app
supported_content_types = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
}

# Define the pages for the application/renewal, in order
application_pages = {
    "get_ready": "app:get_ready",
    "account": "app:account",
    "address": "app:address",
    "household": "app:household",
    "household_members": "app:household_members",
    "eligibility_programs": "app:programs",
    "files": "app:files",
}

# Define form choices for rent/own and duration at address
rent_own_choices = (
    ("rent", "Rent"),
    ("own", "Own"),
)
duration_at_address_choices = (
    ("More than 3 Years", "More than 3 Years"),
    ("1 to 3 Years", "1 to 3 Years"),
    ("Less than a Year", "Less than a Year"),
)

# Define the allowable variables for use to render text defined in
# PlatformSettings
platform_settings_render_variables = {
    "platform organization": {
        # This is in PlatformSettings, which is the 'base' relative model
        "relative_model": "base",
        "field": "organization",
    },
    "platform name": {
        # This is in PlatformSettings, which is the 'base' relative model
        "relative_model": "base",
        "field": "name",
    },
    "vendor name": {
        # This is expected in the 'current' relative model to where it will be
        # used
        "relative_model": "current",
        "field": "name",
    },
    "phone number": {
        # This is in PlatformSettings, which is the 'base' relative model
        "relative_model": "base",
        "field": "phonenumber",
    },
    "email": {
        # This is in PlatformSettings, which is the 'base' relative model
        "relative_model": "base",
        "field": "email",
    },
}
