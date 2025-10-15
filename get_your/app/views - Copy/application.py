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

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.forms.utils import ErrorList
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse

from app.backend import form_page_number
from app.backend import login

# from app.backend import save_renewal_action
from app.decorators import set_update_mode
from app.forms import UserForm
from app.forms import UserUpdateForm
from monitor.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()


@set_update_mode
def account(request, **kwargs):
    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        update_mode = (
            request.session.get("update_mode")
            if request.session.get("update_mode")
            else False
        )
        renewal_mode = (
            request.session.get("renewal_mode")
            if request.session.get("renewal_mode")
            else False
        )

        if request.method == "POST":
            log.debug(
                "Leaving function (POST)",
                function="account",
                user_id=request.user.id,
            )

            try:
                existing = request.user
                if (
                    update_mode
                    or renewal_mode
                    or (
                        hasattr(request.user, "has_viewed_dashboard")
                        and not request.user.has_viewed_dashboard
                    )
                ):
                    form = UserUpdateForm(request.POST, instance=existing)
                else:
                    form = UserForm(request.POST, instance=existing)
            except (AttributeError, ObjectDoesNotExist):
                form = UserForm(request.POST or None)

            # Checking the `has_viewed_dashboard` attribute of the user object
            # allows us to determine if the user has already completed the application
            # or if they're returning to update their information from the initial application
            if form.is_valid() and (
                update_mode
                or renewal_mode
                or (
                    hasattr(request.user, "has_viewed_dashboard")
                    and not request.user.has_viewed_dashboard
                )
            ):
                instance = form.save(commit=False)

                # Set the attributes to let pre_save know to save history
                # instance.update_mode = update_mode
                # instance.renewal_mode = renewal_mode
                instance.save()

                if renewal_mode:
                    # Call save_renewal_action after .save() so as not to save
                    # renewal metadata as data updates
                    # save_renewal_action(request, "account")
                    return JsonResponse({"redirect": f"{reverse('app:address')}"})
                if (
                    hasattr(request.user, "has_viewed_dashboard")
                    and not request.user.has_viewed_dashboard
                ):
                    return JsonResponse({"redirect": f"{reverse('app:address')}"})
                return JsonResponse(
                    {
                        "redirect": f"{reverse('users:detail', kwargs={'pk': request.user.id})}?page_updated=account",
                    },
                )
            if form.is_valid():
                passwordCheck = form.passwordCheck()
                passwordCheckDuplicate = form.passwordCheckDuplicate()
                # AJAX data function below, sends data to AJAX function in account.html. If client makes a mistake in password, AJAX lets them know, no page refresh
                # if passwordCheck finds an error like too common a password, no numbers, etc.
                if passwordCheck != None:
                    data = {
                        "result": "error",
                        "message": passwordCheck,
                    }
                    return JsonResponse(data)
                # AJAX data function below, sends data to AJAX function in account.html. If client makes a mistake in password, AJAX lets them know, no page refresh
                # Checks if password is the same as the "Enter Password Again" Field
                if str(passwordCheckDuplicate) != str(form.cleaned_data["password"]):
                    data = {
                        "result": "error",
                        "message": passwordCheckDuplicate,
                    }
                    return JsonResponse(data)

                try:
                    user = form.save()
                    login(request, user)

                    log.info(
                        "User account creation successful",
                        function="account",
                        user_id=user.id,
                    )

                    data = {
                        "result": "success",
                    }
                    return JsonResponse(data)
                except AttributeError:
                    log.warning(
                        f"Login failed. User is: {user}",
                        function="account",
                        user_id=request.user.id,
                    )

                return redirect(reverse("app:address"))

            # AJAX data function below, sends data to AJAX function in account.html, if clients make a mistake via email or phone number, page lets them know and DOESN'T refresh web page
            # let's them know via AJAX
            error_messages = dict(form.errors.items())

            # Create message_dict by parsing strings or all items of ErrorList,
            # where applicable. Use the prettified field name as each key
            message_dict = {}
            for keyitm in error_messages:
                val = error_messages[keyitm]

                # Gather the list of error messages and flatten it
                message_list = [[y for y in val] if isinstance(val, ErrorList) else val]
                flattened_messages = [item for items in message_list for item in items]

                # Write the messages as a string
                message_dict.update(
                    {
                        keyitm.replace("_", " ").title(): ". ".join(flattened_messages),
                    },
                )
            # Create error message data by prepending the prettified field name
            # and joining as newlines
            data = {
                "result": "error",
                "message": "\n".join(
                    [f"{keyitm}: {message_dict[keyitm]}" for keyitm in message_dict],
                ),
            }
            return JsonResponse(data)
        log.debug(
            "Entering function (GET)",
            function="account",
            user_id=request.user.id,
        )

        try:
            user = User.objects.get(id=request.user.id)
            form = UserUpdateForm(instance=user)
            update_mode = True
        except Exception:
            form = UserForm()

        return render(
            request,
            "application/account.html",
            {
                "form": form,
                "step": 1,
                "form_page_number": form_page_number,
                "title": "Account",
                "update_mode": update_mode,
                "renewal_mode": renewal_mode,
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
            function="account",
            user_id=user_id,
        )
        raise
