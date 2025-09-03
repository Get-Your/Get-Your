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

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import BadHeaderError
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from logger.wrappers import LoggerWrapper

from app.backend import broadcast_email_pw_reset
from app.backend import login
from app.backend import what_page

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def password_reset_request(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="password_reset_request",
            user_id=request.user.id,
        )

        User = get_user_model()
        if request.method == "POST":
            password_reset_form = PasswordResetForm(request.POST)
            if password_reset_form.is_valid():
                data = password_reset_form.cleaned_data["email"]
                associated_users = User.objects.filter(Q(email=data))
                if associated_users.exists():
                    for user in associated_users:
                        email_template_name = "authentication/password_reset_email.txt"
                        c = {
                            "email": user.email,
                            "domain": "getfoco.fcgov.com",  # 'getfoco.azurewebsites.net' | '127.0.0.1:8000'
                            "site_name": "Get FoCo",
                            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                            "user": user,
                            "token": default_token_generator.make_token(user),
                            "protocol": "http",
                        }
                        email = render_to_string(email_template_name, c)
                        try:
                            broadcast_email_pw_reset(user.email, email)
                        except BadHeaderError:
                            msg = "Invalid header found"
                            log.exception(
                                msg,
                                function="password_reset_request",
                                user_id=request.user.id,
                            )
                            return HttpResponse(msg)
                        return redirect("/password_reset/done/")
                else:
                    return redirect("/password_reset/done/")
        password_reset_form = PasswordResetForm()

        return render(
            request,
            "authentication/password_reset.html",
            {
                "password_reset_form": password_reset_form,
                "title": "Password Reset Request",
            },
        )

    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="password_reset_request",
            user_id=user_id,
        )
        raise


def login_user(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="login_user",
            user_id=request.user.id,
        )

        if request.method == "POST":
            # Try to log in user
            email = request.POST["email"]
            password = request.POST["password"]
            user = authenticate(username=email, password=password)
            # Check if the authentication was successful
            if user is not None:
                login(request, user)
                # Push user to correct page
                # update application_user "modified" per login
                obj = request.user
                obj.save()

                # Push user to correct page

                # If auth_next exists, use it for the redirection
                if request.session.get("auth_next", None) is not None:
                    return redirect(request.session["auth_next"])

                # Workaround for https://github.com/Get-Your/Get-Your/issues/251:
                # existing data in last_renewal_action implies the user logged out
                # during a renewal and therefore should be taken directly to the
                # dashboard
                if request.user.last_renewal_action is not None:
                    return redirect(reverse("app:dashboard"))

                page = what_page(request.user, request)
                log.info(
                    f"Continuing application: what_page() returned {page}",
                    function="login_user",
                    user_id=request.user.id,
                )
                if page == "app:dashboard":
                    return redirect(reverse("app:dashboard"))
                return redirect(reverse("app:notify_remaining"))

            return render(
                request,
                "authentication/login.html",
                {
                    "message": "Invalid username and/or password",
                    "title": "Login",
                },
            )

        # If it turns out user is already logged in but is trying to log in again,
        # run through what_page() to find the correct place
        if request.method == "GET" and request.user.is_authenticated:
            page = what_page(request.user, request)
            log.info(
                f"what_page() returned {page}",
                function="login_user",
                user_id=request.user.id,
            )
            if page == "app:dashboard":
                return redirect(reverse("app:dashboard"))
            return redirect(reverse("app:notify_remaining"))

        # Just give back log in page if none of the above is true
        return render(
            request,
            "authentication/login.html",
            {
                "title": "Login",
            },
        )

    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="login_user",
            user_id=user_id,
        )
        raise
