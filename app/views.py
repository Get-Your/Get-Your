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

from django.shortcuts import render
from monitor.wrappers import LoggerWrapper
from ref.models import EligibilityProgramRef, AddressRef

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# @login_required(redirect_field_name='auth_next')
def eligibility_form(request, **kwargs):
    if request.method == "POST":
        # Handle the program ID and file upload
        # Return to some other page, with a sucess mesage
        pass
    else:
        ami_30_programs = EligibilityProgramRef.objects.filter(is_active=True).filter(ami_threshold=.3).order_by(
                'friendly_name').values_list('friendly_name', flat=True)

        ami_60_programs = EligibilityProgramRef.objects.filter(is_active=True).filter(ami_threshold=.6).order_by(
                'friendly_name').values_list('friendly_name', flat=True)

        print(ami_30_programs)

        return render(
            request,
            'dashboard/new_eligibility.html',
            {
                'title': 'Program Form',
                'ami30_programs': ami_30_programs,
                'ami60_programs': ami_60_programs,
            }
    )
