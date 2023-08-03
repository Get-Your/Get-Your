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


class ValidRouteMiddleware(MiddlewareMixin):
    """
    Middleware that checks if the user is in a valid route and redirects them to the correct page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        if not self.is_valid_route(request):
            # Redirect to the dashboard
            return redirect(reverse("app:dashboard"))

        return response

    def is_valid_route(self, request):
        try:
            resolve(request.path)
            return True
        except Resolver404:
            pass

        return False


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
