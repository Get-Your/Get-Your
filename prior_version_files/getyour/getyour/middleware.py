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

from app.backend import what_page_renewal
from django.core.exceptions import MiddlewareNotUsed
from django.shortcuts import redirect
from django.urls import reverse
from monitor.wrappers import LoggerWrapper

log = LoggerWrapper(logging.getLogger(__name__))


class LoginRequiredMiddleware:
    """
    Middleware that checks if the user is logged in and redirects them to the
    dashboard. The dashboard is always the target because there's no way to
    ensure all parameters for the various states are set properly.

    """

    def __init__(self, get_response):
        """One-time configuration/initialization (upon web server start)."""

        self.get_response = get_response

        raise MiddlewareNotUsed

    def __call__(self, request):
        """Primary call for the middleware."""

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if not request.user.is_authenticated:
            # If the route is in excluded_paths don't do anything
            excluded_paths = [
                reverse("app:index"),
                reverse("app:get_ready"),
                reverse("users:detail"),
                reverse("app:quick_available"),
                reverse("app:quick_not_available"),
                reverse("app:quick_coming_soon"),
                reverse("app:quick_not_found"),
                reverse("app:programs_info"),
                reverse("app:privacy_policy"),
            ]

            # Get the view instance that's handling the current request
            current_path = request.path_info

            # Redirect to login if the current path isn't excluded or includes
            # 'reset'. The login workflow will take over after successful auth
            if not (current_path in excluded_paths or "reset" in current_path):
                return redirect("users:signup")

        # Default to calling the specified view
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


class RenewalModeMiddleware:
    """
    Middleware that checks if the user is in renewal mode and redirects them to the correct page.
    """

    def __init__(self, get_response):
        """One-time configuration/initialization (upon web server start)."""

        self.get_response = get_response

    def __call__(self, request):
        """Primary call for the middleware."""

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # This runs only for getting into the renewal process (the 'renew'
        # button on the dashboard, where 'renewal_mode' is specified as a URL
        # parameter in the GET call)
        if request.GET.get("renewal_mode", False):
            # This session var will be the global bool for renewal_mode
            request.session["renewal_mode"] = True

            if request.user.last_renewal_action:
                what_page = what_page_renewal(request.user.last_renewal_action)
                log.info(
                    f"Continuing renewal: what_page_renewal() returned {what_page}"
                )

                # Redirect to the what_page designation, if exists (None is when
                # all pages have been completed)
                if what_page is not None:
                    return redirect(what_page)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
