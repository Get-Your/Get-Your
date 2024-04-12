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
import pendulum
from pathlib import PurePosixPath

from django.shortcuts import render
from django.core.files.storage import default_storage
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from azure.core.exceptions import ResourceNotFoundError

from app.models import User, EligibilityProgram, EligibilityProgramRD
from app.constants import supported_content_types
from app.backend import file_validation, finalize_application
from app.admin.forms import EligProgramAddForm

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


@staff_member_required
def add_elig_program(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function='add_elig_program',
            user_id=request.user.id,
        )

        # Define the application user (not the admin)
        user = User.objects.get(id=kwargs['user_id'])

        if request.method == "POST":
            log.debug(
                "Leaving function (POST)",
                function='add_elig_program',
                user_id=request.user.id,
            )

            form = EligProgramAddForm(request.POST, request.FILES)

            if form.is_valid():
                file_validated, validation_message = file_validation(
                    request.FILES.getlist('document_path')[0],
                    request.user.id,
                    calling_function='add_elig_program',
                )
                if not file_validated:
                    return render(
                        request,
                        "admin/program_add_elig.html",
                        {
                            'form': form,
                            'error_message': validation_message,
                            # Set some page-specific text
                            'site_header': 'Get FoCo administration',
                            'title': f"Add Eligibility Program for {user.full_name}",
                            'site_title': 'Get FoCo administration',
                        },
                    )

                # Create the program object
                instance = EligibilityProgram.objects.create(
                    user=user,
                    program=EligibilityProgramRD.objects.get(
                        id=int(form.cleaned_data['program_name'])
                    ),
                )
                fileNames = []
                
                # Save the upload to blob storage
                fileobj = request.FILES.getlist('document_path')[0]
                instance.document_path.save(
                    pendulum.now(
                        'utc'
                    ).format(
                        f"YYYY-MM-DD[T]HHmmss[Z_1_{fileobj}]"
                    ),
                    fileobj,
                )
                fileNames.append(str(instance.document_path))

                # Reformat document_path in the database to match the app
                instance.document_path = str(fileNames)
                instance.save()

                # Add a log entry to UserAdmin for this new program
                _ = LogEntry.objects.log_action(
                    user_id=request.user.id,
                    # Use the target (user) object from here
                    content_type_id=ContentType.objects.get_for_model(user).pk,
                    object_id=user.id,
                    object_repr=str(user),
                    action_flag=CHANGE,
                    change_message=f'Added User eligibility program "{str(instance)}".'
                )

                # Add a log entry to EligibilityProgram admin that the program
                # was added
                _ = LogEntry.objects.log_action(
                    user_id=request.user.id,
                    # Use the target (eligibility program) object from here
                    content_type_id=ContentType.objects.get_for_model(instance).pk,
                    object_id=instance.id,
                    object_repr=str(instance),
                    action_flag=ADDITION,
                    change_message=f'Added User eligibility program "{str(instance)}".'
                )

                # Finalize the application with the new program, if applicable
                if user.last_completed_at is not None:
                    prev_income_as_fraction_of_ami = user.household.income_as_fraction_of_ami
                    _ = finalize_application(user, update_user=False)

                    # Add a log entry to UserAdmin if income was changed
                    # IQ Program changes are planned for a later date
                    if user.household.income_as_fraction_of_ami != prev_income_as_fraction_of_ami:
                        _ = LogEntry.objects.log_action(
                            user_id=request.user.id,
                            # Use the target (user) object from here
                            content_type_id=ContentType.objects.get_for_model(user).pk,
                            object_id=user.id,
                            object_repr=str(user),
                            action_flag=CHANGE,
                            change_message='Changed Income relative to AMI.'
                        )

                return render(
                    request,
                    "admin/program_add_elig.html",
                    {
                        'form': form,
                        'success_message': "Program added successfully. Close this window and refresh the User page to view it.",
                        # Set some page-specific text
                        'site_header': 'Get FoCo administration',
                        'title': f"Add Eligibility Program for {user.full_name}",
                        'site_title': 'Get FoCo administration',
                    },
                )
                

        
        else:
            log.debug(
                "Entering function (GET)",
                function='add_elig_program',
                user_id=request.user.id,
            )

            form = EligProgramAddForm()

        return render(
            request,
            "admin/program_add_elig.html",
            {
                'form': form,
                # Set some page-specific text
                'site_header': 'Get FoCo administration',
                'title': f"Add Eligibility Program for {user.full_name}",
                'site_title': 'Get FoCo administration',
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
            function='add_elig_program',
            user_id=user_id,
        )
        raise
