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
import logging

from django.shortcuts import render, redirect
from django.urls import reverse, resolve
from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

from app.backend import what_page_renewal
from logger.wrappers import LoggerWrapper


log = LoggerWrapper(logging.getLogger(__name__))


class LoginRequiredMiddleware:
    """
    Middleware that checks if the user is logged in and redirects them to the
    dashboard. The dashboard is always the target because there's no way to
    ensure all parameters for the various states are set properly.

    """

    def __init__(self, get_response):
        """ One-time configuration/initialization (upon web server start). """

        self.get_response = get_response

        raise MiddlewareNotUsed

    def __call__(self, request):
        """ Primary call for the middleware. """

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if not request.user.is_authenticated:
            # If the route is in excluded_paths don't do anything
            excluded_paths = [
                reverse('app:login'),
                reverse('app:index'),
                reverse('app:get_ready'),
                reverse('app:account'),
                reverse('app:quick_available'),
                reverse('app:quick_not_available'),
                reverse('app:quick_coming_soon'),
                reverse('app:quick_not_found'),
                reverse('app:programs_info'),
                reverse('app:privacy_policy'),
                reverse('app:password_reset'),
                reverse('password_reset_done'),
                reverse('password_reset_complete'),
            ]

            # Get the view instance that's handling the current request
            current_path = request.path_info
            
            # Redirect to login if the current path isn't excluded or includes
            # 'reset'. The login workflow will take over after successful auth
            if not (current_path in excluded_paths or 'reset' in current_path):
                return redirect("app:login")

        # Default to calling the specified view
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    

class ValidRouteMiddleware:
    """
    Middleware that checks if the user is in a valid route. If not, a 404 error
    is raised.

    This exists separately from the internal Django "valid route" so that it
    can be called before LoginRequiredMiddleware and therefore doesn't make
    the user login before discovering they have a bad URL.

    """

    def __init__(self, get_response):
        """ One-time configuration/initialization (upon web server start). """

        self.get_response = get_response

    def __call__(self, request):
        """ Primary call for the middleware. """

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # If the 'auth_next' URL param (from login_required) exists, use the
        # specified path
        if request.GET.get('auth_next', None) is not None:
            # Add to the session var and remove from request
            request.session['auth_next'] = request.GET['auth_next']
        # Remove the redirect from session vars as we're going to that page
        if request.session.get('auth_next', None) is not None:
            if request.session['auth_next'] == request.path:
                del request.session['auth_next']

        # Try to resolve the path. This will return a 404 if invalid.
        _ = resolve(request.path)

        # Default to calling the specified view
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """ Final step before processing the view. """

        # When attempting to access a page ('GET'), check for whether 'direct
        # access' is allowed
        if request.method == "GET":
            # If 'direct user access' is not allowed (not True) and the request
            # wasn't referred from somewhere else, return a 404
            # Default to allow_direct_user==True to allow the user through if 
            # allow_direct_user was accidentally omitted from URLconf
            if not view_kwargs.get('allow_direct_user', True) and request.META.get('HTTP_REFERER') is None:
                return render(request, '405.html', status=405)
            
        # Continue through the middleware stack
        return None


class RenewalModeMiddleware:
    """
    Middleware that checks if the user is in renewal mode and redirects them to the correct page.
    """

    def __init__(self, get_response):
        """ One-time configuration/initialization (upon web server start). """
        
        self.get_response = get_response

    def __call__(self, request):
        """ Primary call for the middleware. """

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # This runs only for getting into the renewal process (the 'renew'
        # button on the dashboard, where 'renewal_mode' is specified as a URL
        # parameter in the GET call)
        if request.GET.get('renewal_mode', False):
            # This session var will be the global bool for renewal_mode
            request.session['renewal_mode'] = True

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


class FirstViewMiddleware:
    """
    Middleware that determines if this is the first view by a user and logs
    an 'app started' message.
    
    """

    def __init__(self, get_response):
        """ One-time configuration/initialization (upon web server start). """
        
        self.get_response = get_response

    def __call__(self, request):
        """ Primary call for the middleware. """

        if 'first_view_recorded' not in request.session:
            log.info(
                f"Starting instance: app version {settings.CODE_VERSION}",
                function='FirstViewMiddleware',
            )

            # Set the session var so this isn't called again for the user
            request.session['first_view_recorded'] = True

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
            
        return response