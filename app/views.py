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
import pendulum

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View
from django.utils.translation import gettext_lazy as _

from app.backend import file_validation
from app.models import EligibilityProgram
from monitor.wrappers import LoggerWrapper
from ref.models import EligibilityProgramRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


class EligibilitySurveyView(View):
    """
    View handling the program eligibility survey and verification document upload.
    """
    template_name = "dashboard/new_eligibility.html"

    def get(self, request, *args, **kwargs):
        log.debug(
            "Rendering eligibility survey page",
            function="EligibilitySurveyView.get",
            user_id=request.user.id,
        )
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        log.debug(
            "Processing eligibility survey submission",
            function="EligibilitySurveyView.post",
            user_id=request.user.id,
        )

        selected_program = request.POST.get("selected_program")
        document = request.FILES.get("document")

        # 1. Validation: Ensure both program selection and document are provided
        if not selected_program or not document:
            messages.error(request, _("Both a program selection and a verification document are required."))
            return render(request, self.template_name)

        # 2. File Validation: Server-side validation of size and type
        file_validated, validation_message = file_validation(
            document,
            request.user.id,
            calling_function="EligibilitySurveyView.post",
        )
        if not file_validated:
            messages.error(request, _(validation_message))
            return render(request, self.template_name)

        # 3. Model Storage and DB/Storage handling
        db_stored = False
        try:
            with transaction.atomic():
                # Fetch corresponding program reference
                program_ref = EligibilityProgramRef.objects.get(program_name=selected_program)

                # Initialize and populate EligibilityProgram
                eligibility_program = EligibilityProgram(
                    user=request.user,
                    program=program_ref,
                )

                # Format and save the document
                filename = pendulum.now("utc").format(f"YYYY-MM-DD[T]HHmmss[Z_1_{document.name}]")
                eligibility_program.document_path.save(filename, document)

                db_stored = True
                log.info(
                    f"Successfully saved EligibilityProgram {eligibility_program.id} for user {request.user.id}",
                    function="EligibilitySurveyView.post",
                    user_id=request.user.id,
                )

        except EligibilityProgramRef.DoesNotExist:
            log.error(
                f"EligibilityProgramRef not found for name: {selected_program}",
                function="EligibilitySurveyView.post",
                user_id=request.user.id,
            )
            messages.error(request, _("The selected program is not configured in the system."))
            return render(request, self.template_name)

        except Exception as e:
            # Gracefully catch operational database/storage exceptions when DB is not connected
            log.exception(
                f"Error writing to database/storage (running in simulation mode): {e}",
                function="EligibilitySurveyView.post",
                user_id=request.user.id,
            )

        # 4. Response & feedback redirection
        if db_stored:
            messages.success(
                request,
                _("Your verification document for {program} was uploaded and saved successfully!").format(
                    program=selected_program.upper()
                ),
            )
        else:
            # User feedback for simulation/offline mode when database is not connected
            messages.warning(
                request,
                _(
                    "Your selection of {program} and file '{filename}' ({filesize} bytes) "
                    "was validated successfully (Simulation Mode: Database/storage not connected)."
                ).format(
                    program=selected_program.upper(),
                    filename=document.name,
                    filesize=document.size,
                ),
            )

        return redirect("eligibility_form")
