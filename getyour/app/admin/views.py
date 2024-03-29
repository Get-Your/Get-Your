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
import base64
from pathlib import PurePosixPath

from django.shortcuts import render
from django.core.files.storage import default_storage
from django.contrib.admin.views.decorators import staff_member_required
from azure.core.exceptions import ResourceNotFoundError

from app.constants import supported_content_types
from logger.wrappers import LoggerWrapper


# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


@staff_member_required
def view_file(request, blob_name, **kwargs):
    try:
        log.debug(
            "Entering function",
            function='view_file',
            user_id=request.user.id,
        )

        # Open the blob and extract the data
        file = default_storage.open(blob_name)
        try:
            blob_data = b''
            for chunk in file.chunks():
                blob_data += chunk
        except ResourceNotFoundError as e:
            log.exception(
                f"ResourceNotFoundError: {e}",
                function='view_file',
                user_id=request.user.id,
            )
            raise ResourceNotFoundError(message=e)
        
        # Gather the content type from the blob_name extension
        blob_name_path = PurePosixPath(blob_name)
        # Use the lowercase suffix (without the leading dot) as the key to the
        # supported_content_types dict
        content_type = supported_content_types[blob_name_path.suffix[1:].lower()]

        return render(
            request,
            'admin/view_file.html',
            {
                'blob_data': base64.b64encode(blob_data).decode('utf-8'),
                'content_type': content_type,
            },
        )
    
    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            'Uncaught view-level exception',
            function='view_file',
            user_id=user_id,
        )
        raise
