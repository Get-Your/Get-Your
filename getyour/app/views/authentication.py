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
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, get_user_model, authenticate
from django.http import HttpResponse
from django.core.mail import BadHeaderError
from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from app.backend import authenticate, what_page, broadcast_email_pw_reset


def password_reset_request(request):
    User = get_user_model()
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    email_template_name = "authentication/password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': 'getfoco.fcgov.com',  # 'getfoco.azurewebsites.net' | '127.0.0.1:8000'
                        'site_name': 'Get FoCo',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        broadcast_email_pw_reset(user.email, email)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                    return redirect("/password_reset/done/")
            else:
                return redirect("/password_reset/done/")
    password_reset_form = PasswordResetForm()

    return render(
        request,
        "authentication/password_reset.html",
        {
            "password_reset_form": password_reset_form,
            'title': "Password Reset Request",
        },
    )


def login_user(request):
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
            page = what_page(request.user, request)
            print(page)
            if page == "app:dashboard":
                return redirect(reverse("app:dashboard"))
            else:
                return redirect(reverse("app:notify_remaining"))

        else:
            return render(
                request,
                "authentication/login.html",
                {
                    "message": "Invalid username and/or password",
                    'title': "Login",
                },
            )

    # If it turns out user is already logged in but is trying to log in again,
    # run through what_page() to find the correct place
    if request.method == "GET" and request.user.is_authenticated:
        page = what_page(request.user, request)
        print(page)
        if page == "app:dashboard":
            return redirect(reverse("app:dashboard"))
        else:
            return redirect(reverse("app:notify_remaining"))

    # Just give back log in page if none of the above is true
    else:
        return render(
            request,
            "authentication/login.html",
            {
                'title': "Login",
            },
        )