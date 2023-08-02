from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from app.backend import what_page_renewal


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
