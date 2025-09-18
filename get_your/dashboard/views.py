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

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse

from app.backend import address_check
from app.backend import enable_renew_now
from app.backend import get_users_iq_programs
from app.models import IQProgram
from monitor.wrappers import LoggerWrapper
from ref.models import Address as AddressRef
from ref.models import IQProgram as IQProgramRef

from .forms import FeedbackForm

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


@login_required()
def dashboard(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="dashboard",
            user_id=request.user.id,
        )

        # Check if the users renewal_mode session variable is set to True and
        # retrieve renewal_eligible and renewal_ineligible session vars
        renewal_eligible = request.session.get("renewal_eligible", [])
        renewal_ineligible = request.session.get("renewal_ineligible", [])

        app_renewed = False
        if request.session.get("renewal_mode", False) and request.session.get(
            "app_renewed",
            False,
        ):
            app_renewed = True
            request.session["renewal_mode"] = False
            request.session["app_renewed"] = False
            del request.session["renewal_eligible"]
            del request.session["renewal_ineligible"]
            log.info(
                "Renewal completed successfully",
                function="dashboard",
                user_id=request.user.id,
            )

        # Reset update and renewal mode session vars; dashboard() is the
        # starting point for each of these modes, so this provides a blank slate
        # Note that this is done *after* the check to set `app_renewed`
        request.session["update_mode"] = False
        request.session["renewal_mode"] = False

        qualified_programs = 0
        active_programs = 0
        pending_programs = 0
        renewal_programs = 0

        # Get the user's eligibility address
        eligibility_address = AddressRef.objects.filter(
            id=request.user.address.eligibility_address_id,
        ).first()
        users_iq_programs = get_users_iq_programs(
            request.user.id,
            request.user.household.income_as_fraction_of_ami,
            eligibility_address,
        )
        for program in users_iq_programs:
            # If the program's visibility is 'block' or the status is `ACTIVE` or `PENDING`, it means the user is eligible for the program
            # so we'll count it for their total number of programs they qualify for
            if (
                program.status_for_user == "ACTIVE"
                or program.status_for_user == "PENDING"
                or program.status_for_user == "RENEWAL"
                or program.status_for_user == ""
            ):
                qualified_programs += 1

            # If a program's status_for_user is 'PENDING' add 1 to the pending number and subtract 1 from the qualified_programs
            if program.status_for_user == "PENDING":
                pending_programs += 1
                qualified_programs -= 1
            # If a program's status_for_user is 'ACTIVE' add 1 to the active number and subtract 1 from the qualified_programs
            elif program.status_for_user == "ACTIVE":
                active_programs += 1
                qualified_programs -= 1
            elif program.status_for_user == "RENEWAL":
                renewal_programs += 1
                qualified_programs -= 1

        # By default we assume the user has viewed the dashboard, but if they haven't
        # we set the proxy_viewed_dashboard flag to false and update the user
        # in the database to say that they have viewed the dashboard. This obviates
        # the need to create some AJAX call to a Django template to update the database
        # when the user views the dashboard.
        proxy_viewed_dashboard = True
        if request.user.has_viewed_dashboard == False:
            proxy_viewed_dashboard = False
            request.user.has_viewed_dashboard = True
            request.user.save()

        # Parse and stringify renewal_eligible and renewal_ineligible
        if len(renewal_eligible) == 1:
            renewal_eligible_str = f"{renewal_eligible[-1]} was successfully renewed!"
        elif len(renewal_eligible) > 1:
            renewal_eligible_str = (
                "{plur}{oxcom} and {sing} were successfully renewed!".format(
                    plur=", ".join(renewal_eligible[:-1]),
                    oxcom="," if len(renewal_eligible) > 2 else "",
                    sing=renewal_eligible[-1],
                )
            )
        else:
            renewal_eligible_str = ""

        ineligible_pre = "Unfortunately, you are no longer qualified for"
        ineligible_post = (
            f"If you think this is in error, please email {settings.CONTACT_EMAIL}"
        )
        if len(renewal_ineligible) == 1:
            renewal_ineligible_str = (
                f"{ineligible_pre} {renewal_ineligible[-1]}. {ineligible_post}"
            )
        elif len(renewal_ineligible) > 1:
            renewal_ineligible_str = "{pre} {plur}{oxcom} and {sing}. {pst}".format(
                plur=", ".join(renewal_ineligible[:-1]),
                oxcom="," if len(renewal_ineligible) > 2 else "",
                sing=renewal_ineligible[-1],
                pre=ineligible_pre,
                pst=ineligible_post,
            )
        else:
            renewal_ineligible_str = ""

        return render(
            request,
            "dashboard/dashboard.html",
            {
                "title": "Get FoCo Dashboard",
                "dashboard_color": "var(--yellow)",
                "program_list_color": "white",
                "Settings_color": "white",
                "Privacy_Policy_color": "white",
                "iq_programs": users_iq_programs,
                "qualified_programs": qualified_programs,
                "pending_programs": pending_programs,
                "active_programs": active_programs,
                "renewal_programs": renewal_programs,
                "proxy_viewed_dashboard": proxy_viewed_dashboard,
                "badge_visible": request.user.household.is_income_verified,
                "app_renewed": app_renewed,
                "renewal_eligible": renewal_eligible_str,
                "renewal_ineligible": renewal_ineligible_str,
                "enable_renew_now": enable_renew_now(request.user.id),
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
            function="dashboard",
            user_id=user_id,
        )
        raise


@login_required()
def quick_apply(request, iq_program, **kwargs):
    try:
        in_gma_with_no_service = False

        # Get the IQProgramRef object for the iq_program
        iq_program = IQProgramRef.objects.get(program_name=iq_program)

        log.debug(
            f"Entering function for {iq_program.program_name}",
            function="quick_apply",
            user_id=request.user.id,
        )

        # Get the user's get_users_iq_programs and check if
        # the IQProgramRef object is in the list. If it is not,
        # throw a 500 error, else continue
        eligibility_address = AddressRef.objects.filter(
            id=request.user.address.eligibility_address_id,
        ).first()
        users_iq_programs = get_users_iq_programs(
            request.user.id,
            request.user.household.income_as_fraction_of_ami,
            eligibility_address,
        )
        if iq_program not in users_iq_programs:
            msg = f"User is not eligible for {iq_program.program_name}"
            log.error(
                msg,
                function="quick_apply",
                user_id=request.user.id,
            )
            raise Exception(msg)

        # Check if the user and program already exist in the IQProgram table
        # If they do not, create a new IQProgram object
        if not IQProgram.objects.filter(
            user_id=request.user.id,
            program_id=iq_program.id,
        ).exists():
            # Create and save a new IQProgram object with the user_id and program_id
            IQProgram.objects.create(user_id=request.user.id, program_id=iq_program.id)

        if iq_program.program_name == "connexion":
            # Get the user's address from the AddressRef table by joining the eligibility_address_id
            # to the AddressRef table's id
            addr = AddressRef.objects.get(
                id=request.user.address.eligibility_address_id,
            )
            # Check for Connexion services
            # Recreate the relevant parts of addressDict as if from validate_usps()
            address_dict = {
                "AddressValidateResponse": {
                    "Address": {
                        "Address2": addr.address1,
                        "Zip5": addr.zip_code,
                    },
                },
            }
            is_in_gma, has_isp_service = address_check(address_dict)
            # Connexion (Internet Service Provider) status unknown, but since isInGMA==True at this point in
            # the application, Connexion will be available at some point
            if is_in_gma and not has_isp_service:  # this covers both None and False
                in_gma_with_no_service = True

        return render(
            request,
            "dashboard/quick_apply.html",
            {
                "program_name": iq_program.program_name.title(),
                "title": f"{iq_program.program_name.title()} Application Complete",
                "in_gma_with_no_service": in_gma_with_no_service,
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
            function="quick_apply",
            user_id=user_id,
        )
        raise


@login_required()
def user_settings(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="user_settings",
            user_id=request.user.id,
        )

        request.session["update_mode"] = False
        # Get the success query string parameter
        page_updated = request.GET.get("page_updated")
        if page_updated:
            request.session["page_updated"] = page_updated
            return redirect(reverse("users:detail", kwargs={"pk": request.user.id}))

        if "page_updated" in request.session:
            page_updated = request.session.get("page_updated")
            del request.session["page_updated"]
        else:
            page_updated = None

        return render(
            request,
            "dashboard/user_settings.html",
            {
                "dashboard_color": "white",
                "program_list_color": "white",
                "Settings_color": "var(--yellow)",
                "Privacy_Policy_color": "white",
                "name": request.user.first_name,
                "lastName": request.user.last_name,
                "email": request.user.email,
                "routes": {
                    "account": reverse("users:detail", kwargs={"pk": request.user.id}),
                    "address": reverse("app:address"),
                    "household": reverse("app:household"),
                },
                "page_updated": json.dumps(
                    {"page_updated": page_updated},
                    cls=DjangoJSONEncoder,
                ),
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
            function="user_settings",
            user_id=user_id,
        )
        raise


# Note that auth is required for this only because the dashboard sidenav is
# embedded in privacy.html
# TODO: determine why this is different than landing.privacy_policy
@login_required()
def privacy(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="privacy",
            user_id=request.user.id,
        )

        return render(
            request,
            "dashboard/privacy.html",
            {
                "dashboard_color": "white",
                "program_list_color": "white",
                "Settings_color": "white",
                "Privacy_Policy_color": "var(--yellow)",
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
            function="privacy",
            user_id=user_id,
        )
        raise


@login_required()
def qualified_programs(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="qualified_programs",
            user_id=request.user.id,
        )

        # Get the user's eligibility address
        eligibility_address = AddressRef.objects.filter(
            id=request.user.address.eligibility_address_id,
        ).first()
        users_iq_programs = get_users_iq_programs(
            request.user.id,
            request.user.household.income_as_fraction_of_ami,
            eligibility_address,
        )

        order_by = request.GET.get("order_by")
        if order_by and order_by == "eligible":
            users_iq_programs = sorted(
                users_iq_programs,
                key=lambda x: (x.status_for_user, x.status_for_user),
            )
        elif order_by:
            users_iq_programs = sorted(
                users_iq_programs,
                key=lambda x: (
                    x.status_for_user.lower() != order_by,
                    x.status_for_user,
                ),
            )

        return render(
            request,
            "dashboard/qualified_programs.html",
            {
                "title": "Qualified Programs",
                "dashboard_color": "white",
                "program_list_color": "var(--yellow)",
                "Settings_color": "white",
                "Privacy_Policy_color": "white",
                "iq_programs": users_iq_programs,
                "enable_renew_now": enable_renew_now(request.user.id),
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
            function="qualified_programs",
            user_id=user_id,
        )
        raise


def feedback(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="feedback",
            user_id=request.user.id,
        )

        if request.method == "POST":
            form = FeedbackForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect(reverse("app:feedback_received"))

    # General view-level exception catching
    except:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="feedback",
            user_id=user_id,
        )
        raise


def feedback_received(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="feedback_received",
            user_id=request.user.id,
        )

        return render(
            request,
            "dashboard/feedback_received.html",
            {
                "title": "Feedback Received",
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
            function="feedback_received",
            user_id=user_id,
        )
        raise


@login_required()
def programs_list(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="programs_list",
            user_id=request.user.id,
        )

        # Get the user's eligibility address
        eligibility_address = AddressRef.objects.filter(
            id=request.user.address.eligibility_address_id,
        ).first()
        users_iq_programs = get_users_iq_programs(
            request.user.id,
            request.user.household.income_as_fraction_of_ami,
            eligibility_address,
        )
        return render(
            request,
            "dashboard/programs_list.html",
            {
                "page_title": "Programs List",
                "dashboard_color": "white",
                "program_list_color": "var(--yellow)",
                "Settings_color": "white",
                "Privacy_Policy_color": "white",
                "title": "Programs List",
                "iq_programs": users_iq_programs,
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
            function="programs_list",
            user_id=user_id,
        )
        raise


@login_required()
def apply_now_modal(request, **kwargs):
    if request.method == "POST":
        # This alone will trigger a toast (displaying showMessage) and *nothing
        # else* (the 204 status indicates that the request has succeeded but
        # the browser doesn't need to navigate away (or reload) the page
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/204)
        # The 'applyNowStatusChanged' part of `hx-trigger` allows reload of only
        # the element(s) that are affected; use the following attributes in the
        # containing tag of each target element to reload:
        #     hx-trigger="load, applyNowStatusChanged from:body"
        #     hx-get="{% url '<view that fills the target element>' %}"
        #     hx-target="this"
        # What this does is tell the element to fill itself (via hx-target=
        # "this") with data from the hx-get link, both on page load and when
        # 'applyNowStatusChanged' is received in the hx-trigger header from
        # any element in <body>
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "applyNowStatusChanged": None,
                        "showMessage": "Privacy Policy accepted.",
                    },
                ),
            },
        )

    return render(
        request,
        "dashboard/vendor_privacy_policy.html",
        {
            "policy_text": "Lorem ipsum...",
        },
    )
