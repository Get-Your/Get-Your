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

from django.contrib.auth import get_user_model

from monitor.wrappers import LoggerWrapper
from ref.models import IQProgram as IQProgramRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()


def get_iqprogram_requires_fields():
    """
    Gather all `requires_` fields in the IQProgramRef model along with their
    corresponding AddressRef Boolean.

    """
    field_prefix = "requires_"
    req_fields = [
        (x.name, x.name.replace(field_prefix, ""))
        for x in IQProgramRef._meta.fields
        if x.name.startswith(field_prefix)
    ]

    return req_fields
