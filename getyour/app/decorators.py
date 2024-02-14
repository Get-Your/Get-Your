"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2023

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
from functools import wraps
from django.shortcuts import redirect


def set_user_mode(view_func):
    """
    Decorator to set the update mode in the session.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get the update_mode and renewal_mode query string parameter
        update_mode_set = request.GET.get('update_mode')
        renewal_mode_set = request.GET.get('renewal_mode')

        # For update_mode, redirect queries to the requested path
        # Check explicitly in case the query string is used another way later
        if update_mode_set == '1':
            # This session var will be the global bool for update_mode
            request.session['update_mode'] = True
            return redirect(request.path)
        
        # For renewal_mode, just set the session var and continue on the
        # prescribed path
        if renewal_mode_set == '1':
            request.session['renewal_mode'] = True

        # Call the original view function
        response = view_func(request, *args, **kwargs)
        return response

    return wrapper
