from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from app.backend import what_page_renewal


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Middleware that checks if the user is logged in and redirects them to the correct page.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            # If the route is in excluded_paths don't do anything
            excluded_paths = [
                reverse('app:login'),
                reverse('app:index'),
                reverse('app:get_ready'),
                reverse('app:account'),
                reverse('app:privacy_policy'),
                reverse('app:password_reset'),
                reverse('app:quick_available'),
                reverse('app:quick_not_available'),
                reverse('app:quick_coming_soon'),
                reverse('app:quick_not_found'),
                reverse('app:programs_info'),
                reverse('app:privacy_policy'),
                reverse('password_reset_done'),
                reverse('password_reset_complete'),
            ]

            current_path = request.path_info
            # Get the view instance that's handling the current request

            if current_path in excluded_paths:
                pass
            elif 'reset' in current_path:
                pass
            else:
                return HttpResponseRedirect(reverse("app:login"))


class ValidRouteMiddleware:
    """
    Middleware that checks if the user is in a valid route. If not, a 404 error
    is raised.

    This exists separately from the internal Django "valid route" so that it
    can be called before LoginRequiredMiddleware and therefore doesn't make
    the user login before discovering they have a bad URL.

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Try to resolve the path. This will return a 404 if invalid.
        _ = resolve(request.path)

        # Default to calling the specified view
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


class RenewalModeMiddleware(MiddlewareMixin):
    """
    Middleware that checks if the user is in renewal mode and redirects them to the correct page.
    """

    def process_request(self, request):
        if request.GET.get('renewal_mode', False):
            # This session var will be the global bool for renewal_mode
            request.session['renewal_mode'] = True

            if request.user.last_renewal_action:
                what_page = what_page_renewal(request.user.last_renewal_action)
                return redirect(what_page)
