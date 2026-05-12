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

import httpagentparser
import magic
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_auth_login
from django.core.files.uploadedfile import UploadedFile

from app.constants import supported_content_types
from monitor.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()


def login(request, user):
    django_auth_login(request, user)

    # Try to log user agent data
    try:
        log.info(
            "User logged in; agent is {}".format(
                httpagentparser.simple_detect(request.META["HTTP_USER_AGENT"]),
            ),
            function="login",
            user_id=request.user.id,
        )
    except Exception:
        log.exception(
            "HTTP agent parsing failed!",
            function="login",
            user_id=request.user.id,
        )


def file_validation(
    obj,
    user_id,
    calling_function=None,
):
    """
    Validate the uploaded file with ``python-magic``.

    Returns a tuple of whether validation was successful and any error messages.

    """

    # If obj is an uploaded file, use the first chunk; else, take directly from
    # the buffer
    if isinstance(obj, UploadedFile):
        # If chunk_size is set manually here, python-magic recommends a minimum
        # size of 2048 bytes for proper filetype identification
        # (https://github.com/ahupp/python-magic?tab=readme-ov-file#usage)
        for itm in obj.chunks():
            filetype = magic.from_buffer(itm)
            break
    else:
        filetype = magic.from_buffer(obj)

    # Check if the filetype is in the supported_content_types
    matched_file_extension = next(
        (x for x in supported_content_types if x in filetype.lower()),
        None,
    )
    # If a match is found, return 'success' and the file extension
    if matched_file_extension:
        return (True, matched_file_extension)

    # A match was not found, so return 'failed' and the error message
    log.error(
        "File{} is not a valid file type ({})".format(
            f" from {calling_function}" if calling_function else "",
            filetype,
        ),
        function="file_validation",
        user_id=user_id,
    )
    return (
        False,
        "File is not a valid type. Only these file types are supported: {}".format(
            ", ".join(supported_content_types),
        ),
    )
