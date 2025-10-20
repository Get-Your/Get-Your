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
from urllib.parse import urlencode

import pendulum
import usaddress
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.http import QueryDict
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse
from django.utils.decorators import method_decorator
from formset.views import EditCollectionView

from files.forms import FileUploadForm
from monitor.wrappers import LoggerWrapper
from ref.models import Address as AddressRef
from ref.models import ApplicationPage
from ref.models import EligibilityProgram as EligibilityProgramRef
from ref.models import IQProgram as IQProgramRef

from .backend import broadcast_email
from .backend import broadcast_sms
from .backend import file_validation
from .backend import finalize_application
from .backend import form_page_number
from .backend import get_in_progress_eligiblity_file_uploads

# from .backend import save_renewal_action
from .backend import what_page
from .backend.address import address_check
from .backend.address import finalize_address
from .backend.address import tag_mapping
from .backend.address import validate_usps
from .forms import AddressForm
from .forms import AddressLookupForm
from .forms import HouseholdFormCollection
from .models import Address
from .models import EligibilityProgram
from .models import Household

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def index(request, **kwargs):
    try:
        if request.method == "POST":
            log.debug(
                "Leaving function (POST)",
                function="index",
                user_id=request.user.id,
            )

            form = AddressLookupForm(request.POST or None)
            if form.is_valid():
                try:
                    # Use usaddress to try to parse the input text into an address

                    # Clean the data
                    # Remove 'fort collins' - the multi-word city can confuse the
                    # parser
                    address_str = (
                        form.cleaned_data["address"].lower().replace("fort collins", "")
                    )

                    raw_address_dict, address_type = usaddress.tag(
                        address_str,
                        tag_mapping,
                    )

                    # Only continue to validation, etc if a 'Street Address' is
                    # found by usaddress
                    if address_type != "Street Address":
                        msg = "The address cannot be parsed"
                        log.error(
                            f"{msg}: {raw_address_dict}",
                            function="index",
                            user_id=request.user.id,
                        )
                        raise NameError(msg)

                    # Help out parsing with educated guesses
                    # if 'state' not in raw_address_dict.keys():
                    raw_address_dict["state"] = "CO"
                    # if 'city' not in raw_address_dict.keys():
                    raw_address_dict["city"] = "Fort Collins"

                    log.info(
                        f"Address form submitted: {raw_address_dict}",
                        function="index",
                        user_id=request.user.id,
                    )

                    # Ensure the necessary keys for USPS validation are included
                    usps_keys = [
                        "name",
                        "address_1",
                        "address_2",
                        "city",
                        "state",
                        "zipcode",
                    ]
                    raw_address_dict.update(
                        {
                            key: ""
                            for key in usps_keys
                            if key not in raw_address_dict.keys()
                        },
                    )

                    # Validate to USPS address
                    address_dict = validate_usps(raw_address_dict)

                    # Check for IQ and Connexion (Internet Service Provider) services
                    is_in_gma, has_isp_service = address_check(address_dict)

                    if not is_in_gma:
                        return redirect(reverse("dashboard:quick_not_available"))

                    if is_in_gma and not has_isp_service:
                        # Connexion status unknown, but since is_in_gma==True, it
                        # will be available at some point
                        request.session["address_dict"] = {
                            "address": address_dict["AddressValidateResponse"][
                                "Address"
                            ]["Address2"],
                            "zipCode": address_dict["AddressValidateResponse"][
                                "Address"
                            ]["Zip5"],
                        }

                        # TODO: This is a quick fix for Connexion availability not
                        # working properly (so we removed Connexion from our
                        # messaging completely). This should be cleaned up and the
                        # templates renamed for clarity.
                        return redirect(reverse("dashboard:quick_available"))

                    return redirect(reverse("dashboard:quick_available"))

                except Exception:
                    return redirect(reverse("dashboard:quick_not_found"))

        else:
            log.debug(
                "Entering function (GET)",
                function="index",
                user_id=request.user.id,
            )

            # Check if the app_status query parameter is present
            # If so, check if it is 'in_progress'
            # If it's in progress, redirect to the app:index page
            if "app_status" in request.GET:
                if request.GET["app_status"] == "in_progress":
                    # Set the app_status session variable to 'in_progress'
                    request.session["app_status"] = "in_progress"
                    return redirect(reverse("app:index"))

            # Check if the user is logged in and has the 'app_status' session var
            # set to 'in_progress'
            in_progress_app_saved = False
            if request.user.is_authenticated and "app_status" in request.session:
                if request.session["app_status"] == "in_progress":
                    in_progress_app_saved = True

            # Logout only if user was previously logged in. logout() apparently
            # resets session vars, so it messes with FirstViewMiddleware if it's
            # run indescriminately
            user_id = request.user.id
            if user_id is not None:
                logout(request)
                log.info(
                    "User logged out",
                    function="index",
                    user_id=user_id,
                )

            return render(
                request,
                "landing/index.html",
                {
                    "form": AddressLookupForm(),
                    "in_progress_app_saved": in_progress_app_saved,
                    "iq_programs": IQProgramRef.objects.filter(is_active=True),
                },
            )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="index",
            user_id=user_id,
        )
        raise


def privacy_policy(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="privacy_policy",
            user_id=request.user.id,
        )

        # check if user is logged in
        user_logged_in = False
        if request.user.is_authenticated:
            user_logged_in = True

        return render(
            request,
            "landing/privacy_policy.html",
            {
                "user_logged_in": user_logged_in,
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="privacy_policy",
            user_id=user_id,
        )
        raise


def programs_info(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="programs_info",
            user_id=request.user.id,
        )

        return render(
            request,
            "landing/programs_info.html",
            {
                "title": "Programs List",
                "iq_programs": IQProgramRef.objects.all(),
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="programs_info",
            user_id=user_id,
        )
        raise


def quick_available(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="quick_available",
            user_id=request.user.id,
        )

        return render(
            request,
            "landing/quick_available.html",
            {
                "title": "Quick Connexion Available",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="quick_available",
            user_id=user_id,
        )
        raise


def quick_not_available(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="quick_not_available",
            user_id=request.user.id,
        )

        return render(
            request,
            "landing/quick_not_available.html",
            {
                "title": "Quick Connexion Not Available",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="quick_not_available",
            user_id=user_id,
        )
        raise


def quick_not_found(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="quick_not_found",
            user_id=request.user.id,
        )

        return render(
            request,
            "landing/quick_not_found.html",
            {
                "title": "Quick Connexion Not Found",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="quick_not_found",
            user_id=user_id,
        )
        raise


def quick_coming_soon(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="quick_coming_soon",
            user_id=request.user.id,
        )

        return render(
            request,
            "landing/quick_coming_soon.html",
            {
                "title": "Quick Connexion Coming Soon",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="quick_coming_soon",
            user_id=user_id,
        )
        raise


@login_required()
def notify_remaining(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="notify_remaining",
            user_id=request.user.id,
        )

        page = what_page(request.user, request)
        return render(
            request,
            "application/notify_remaining.html",
            {
                "next_page": page,
                "title": "Notify Remaining Steps",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="notify_remaining",
            user_id=user_id,
        )
        raise


def household_definition(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="household_definition",
            user_id=request.user.id,
        )

        return render(
            request,
            "application/household_definition.html",
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="household_definition",
            user_id=user_id,
        )
        raise


def get_ready(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="get_ready",
            user_id=request.user.id,
        )

        renewal_mode = (
            request.session.get("renewal_mode")
            if request.session.get("renewal_mode")
            else False
        )
        eligiblity_programs = EligibilityProgramRef.objects.filter(
            is_active=True,
        ).order_by("friendly_name")

        # TODO: consider standardizing all pages to use POST instead of linking the next page via the get_ready template (a benefit would be that the proper next page can be calculated here)

        # Check if the next query param is set
        # If so, save the renewal action and redirect to the account page
        if request.GET.get("next", False):
            log.info(
                "Starting renewal process",
                function="get_ready",
                user_id=request.user.id,
            )
            # save_renewal_action(request, "get_ready")
            return redirect("users:detail", kwargs={"pk": request.user.id})
        return render(
            request,
            "application/get_ready.html",
            {
                "step": 0,
                "form_page_number": form_page_number,
                "title": "Ready some Necessary Documents",
                "eligiblity_programs": eligiblity_programs,
                "renewal_mode": renewal_mode,
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="get_ready",
            user_id=user_id,
        )
        raise


@login_required()
def address(request, **kwargs):
    try:
        if request.session.get("application_addresses"):
            del request.session["application_addresses"]

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
                function="address",
                user_id=request.user.id,
            )

            addresses = []

            if not update_mode:
                eligibility_address = {
                    "address1": request.POST["address1"],
                    "address2": request.POST["address2"],
                    "city": request.POST["city"],
                    "state": request.POST["state"],
                    "zipcode": request.POST["zip_code"],
                }
                addresses.append(
                    {
                        "address": eligibility_address,
                        "type": "eligibility",
                        "processed": False,
                    },
                )

            # 'no' means the user has a different mailing address
            # compared to their eligibility address
            if request.POST.get("mailing_address") == "no" or update_mode:
                if request.POST.get("mailing_address") == "no":
                    log.info(
                        "Mailing and eligibility addresses are different",
                        function="address",
                        user_id=request.user.id,
                    )

                mailing_address = {
                    "address1": request.POST["mailing_address1"],
                    "address2": request.POST["mailing_address2"],
                    "city": request.POST["mailing_city"],
                    "state": request.POST["mailing_state"],
                    "zipcode": request.POST["mailing_zip_code"],
                }
                addresses.append(
                    {
                        "address": mailing_address,
                        "type": "mailing",
                        "processed": False,
                    },
                )

            request.session["application_addresses"] = json.dumps(addresses)
            log.info(
                f"Sending to address correction: {request.session['application_addresses']}",
                function="address",
                user_id=request.user.id,
            )
            return redirect(reverse("app:address_correction"))
        log.debug(
            "Entering function (GET)",
            function="address",
            user_id=request.user.id,
        )

        same_address = True
        if update_mode:
            existing = Address.objects.get(user=request.user)
            mailing_address = AddressRef.objects.get(id=existing.mailing_address_id)
            mailing_address = AddressForm(instance=mailing_address)
            # Will be unused if the user is in update mode
            eligibility_address = AddressForm()
        else:
            try:
                existing = Address.objects.get(user=request.user)
                same_address = (
                    existing.mailing_address_id == existing.eligibility_address_id
                )
                eligibility_address = AddressForm(
                    instance=AddressRef.objects.get(id=existing.eligibility_address_id),
                )
                mailing_address = AddressForm(
                    instance=AddressRef.objects.get(id=existing.mailing_address_id),
                )
            except Address.DoesNotExist:
                eligibility_address = AddressForm()
                mailing_address = AddressForm()
        return render(
            request,
            "application/address.html",
            {
                "eligibility_address_form": eligibility_address,
                "mailing_address_form": mailing_address,
                "same_address": same_address,
                "step": 2,
                "form_page_number": form_page_number,
                "title": "Address",
                "update_mode": update_mode,
                "renewal_mode": renewal_mode,
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="address",
            user_id=user_id,
        )
        raise


@login_required()
def address_correction(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="address_correction",
            user_id=request.user.id,
        )

        try:
            addresses = json.loads(request.session["application_addresses"])
            in_progress_address = [
                address for address in addresses if not address["processed"]
            ][0]
            q = QueryDict(urlencode(in_progress_address["address"]), mutable=True)
            q_orig = QueryDict(urlencode(in_progress_address["address"]), mutable=True)

            # Loop through maxLoopIdx+1 times to try different methods of
            # parsing the address
            # Loop 0: as-entered > usaddress > USPS API
            # Loop 1: as-entered with apt/suite keywords replaced with 'unit' >
            # usaddress > USPS API
            # Loop 2: an-entered with keyword replacements > USPS API
            maxLoopIdx = 2
            idx = 0  # starting idx
            flag_needMoreInfo = False  # flag for previous iter needing more info
            while 1:
                log.info(
                    f"Start loop {idx}",
                    function="address_correction",
                    user_id=request.user.id,
                )

                try:
                    if idx in (0, 1):
                        addressStr = "{ad1} {ad2}, {ct}, {st} {zp}".format(
                            ad1=q["address1"].replace("#", ""),
                            ad2=q["address2"].replace("#", ""),
                            ct=q["city"],
                            st=q["state"],
                            zp=q["zipcode"],
                        )

                        try:
                            rawAddressDict, _ = usaddress.tag(
                                addressStr,
                                tag_mapping,
                            )

                        # Go directly to the QueryDict version if there's a usaddress
                        # issue
                        except usaddress.RepeatedLabelError:
                            log.warning(
                                f"Loop index {idx}; Issue found in usaddress labels - continuing as loop 2",
                                function="address_correction",
                                user_id=request.user.id,
                            )
                            idx = 2
                            raise AttributeError

                        # Ensure the necessary keys for USPS validation are included
                        uspsKeys = [
                            "name",
                            "address_1",
                            "address_2",
                            "city",
                            "state",
                            "zipcode",
                        ]
                        rawAddressDict.update(
                            {
                                key: ""
                                for key in uspsKeys
                                if key not in rawAddressDict.keys()
                            },
                        )

                    # Validate to USPS address - use usaddress first, then try
                    # with input QueryDict
                    try:
                        if idx == 2:
                            log.info(
                                f"Loop index {idx}; Attempting USPS validation with input QueryDict: {q}",
                                function="address_correction",
                                user_id=request.user.id,
                            )
                            dict_address = validate_usps(q)
                        else:
                            log.info(
                                f"Loop index {idx}; Attempting USPS validation with rawAddressDict: {rawAddressDict}",
                                function="address_correction",
                                user_id=request.user.id,
                            )
                            dict_address = validate_usps(rawAddressDict)
                        validationAddress = dict_address["AddressValidateResponse"][
                            "Address"
                        ]
                        log.info(
                            f"USPS Validation returned {validationAddress}",
                            function="address_correction",
                            user_id=request.user.id,
                        )

                    except KeyError:
                        if idx == maxLoopIdx:
                            if flag_needMoreInfo:
                                raise TypeError(str_needMoreInfo)
                            raise
                        idx += 1
                        raise AttributeError

                    # Ensure 'Address1' is a valid key
                    if "Address1" not in validationAddress.keys():
                        validationAddress["Address1"] = ""

                    # Kick back to the user if the USPS API needs more information
                    if "ReturnText" in validationAddress.keys():
                        if idx == maxLoopIdx:
                            log.info(
                                "Address not found - end of loop",
                                function="address_correction",
                                user_id=request.user.id,
                            )
                            raise TypeError(validationAddress["ReturnText"])

                        # Continue checking, but flag that this was a result from
                        # the USPS API and store the text
                        flag_needMoreInfo = True
                        str_needMoreInfo = validationAddress["ReturnText"]

                    else:  # success!
                        break

                    if idx == maxLoopIdx:  # this is just here for safety
                        break
                    idx += 1
                    raise AttributeError

                except AttributeError:
                    # Use AttributeError to skip to the end of the loop
                    # Note that idx has already been iterated before this point
                    log.info(
                        f"Loop index {idx}; AttributeError raised to skip to end of loop",
                        function="address_correction",
                        user_id=request.user.id,
                    )
                    if q["address2"] != "":
                        if idx == 1:
                            # For loop 1: if 'ReturnText' is not found and address2 is
                            # not None, remove possible keywords and try again
                            # Note that this will affect later loop iterations
                            log.info(
                                f"Loop index {idx}; Address not found - try to remove/replace keywords",
                                function="address_correction",
                                user_id=request.user.id,
                            )
                            removeList = ["apt", "unit", "#"]
                            for wrd in removeList:
                                q["address2"] = q["address2"].lower().replace(wrd, "")

                            q["address2"] = "Unit {}".format(q["address2"].lstrip())

                    else:
                        # This whole statement updates address2, so if it's blank,
                        # iterate through idx prematurely
                        idx = 2

            # Link to the next page from address_correction.html
            link_next_page = True
            address_feedback = [
                validationAddress["Address2"],
                validationAddress["Address1"],
                validationAddress["City"]
                + " "
                + validationAddress["State"]
                + " "
                + validationAddress["Zip5"],
            ]
            log.info(
                f"address_feedback is: {address_feedback}",
                function="address_correction",
                user_id=request.user.id,
            )

        except TypeError as msg:
            log.info(
                "More address information is needed from user",
                function="address_correction",
                user_id=request.user.id,
            )
            # Don't link to the next page from address_correction.html
            link_next_page = False
            # Only pass to the user for the 'more information is needed' case
            # --This is all that has been tested--
            msg = str(msg)
            if "more information is needed" in msg:
                address_feedback = [
                    msg.replace("Default address: ", ""),
                    "Please press 'back' and re-enter.",
                ]

            else:
                log.info(
                    "Some other issue than 'more information is needed'",
                    function="address_correction",
                    user_id=request.user.id,
                )
                address_feedback = [
                    "Sorry, we couldn't verify this address through USPS.",
                    "Please press 'back' and re-enter.",
                ]

        except KeyError:
            # Don't link to the next page from address_correction.html
            link_next_page = False
            address_feedback = [
                "Sorry, we couldn't verify this address through USPS.",
                "Please press 'back' and re-enter.",
            ]
            log.warning(
                "USPS couldn't figure it out!",
                function="address_correction",
                user_id=request.user.id,
            )

        else:
            request.session["usps_address_validate"] = dict_address
            log.info(
                f"Address match found: {dict_address}",
                function="address_correction",
                user_id=request.user.id,
            )

            # If validation was successful and all address parts are case-insensitive
            # exact matches between entered and validation, skip addressCorrection()

            # Run the QueryDict 'q' to get just dict
            # If just a string input was used (loop idx == 2), use '-' for blanks
            if idx == 2:
                q_orig = {
                    key: q_orig[key] if q[key] != "" else "-" for key in q_orig.keys()
                }
            else:
                q_orig = {key: q_orig[key] for key in q_orig.keys()}
            if (
                "usps_address_validate" in request.session.keys()
                and dict_address["AddressValidateResponse"]["Address"][
                    "Address2"
                ].lower()
                == q_orig["address1"].lower()
                and dict_address["AddressValidateResponse"]["Address"][
                    "Address1"
                ].lower()
                == q_orig["address2"].lower()
                and dict_address["AddressValidateResponse"]["Address"]["City"].lower()
                == q_orig["city"].lower()
                and dict_address["AddressValidateResponse"]["Address"]["State"].lower()
                == q_orig["state"].lower()
                and str(
                    dict_address["AddressValidateResponse"]["Address"]["Zip5"],
                ).lower()
                == q_orig["zipcode"].lower()
            ):
                log.info(
                    "Exact (case-insensitive) address match found",
                    function="address_correction",
                    user_id=request.user.id,
                )
                return redirect(reverse("app:take_usps_address"))

        log.info(
            "Proceeding to user verification of the matched address",
            function="address_correction",
            user_id=request.user.id,
        )

        return render(
            request,
            "application/address_correction.html",
            {
                "step": 2,
                "form_page_number": form_page_number,
                "link_next_page": link_next_page,
                "address_feedback": address_feedback,
                "address_type": in_progress_address["type"],
                "title": "Address Correction",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="address_correction",
            user_id=user_id,
        )
        raise


@login_required()
def take_usps_address(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="take_usps_address",
            user_id=request.user.id,
        )

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

        try:
            # Use the session var created in addressCorrection(), then remove it
            dict_address = request.session["usps_address_validate"]
            del request.session["usps_address_validate"]

            # Check for and store GMA and Connexion status
            is_in_gma, has_connexion = address_check(dict_address)

            # Check if an AddressRef object exists by using the
            # dict_address. If the address is not found, create a new one.
            try:
                dict_ref = dict_address["AddressValidateResponse"]["Address"]
                field_map = [
                    ("Address2", "address1"),
                    ("Address1", "address2"),
                    ("City", "city"),
                    ("State", "state"),
                    ("Zip5", "zip_code"),
                ]
                instance = AddressRef.objects.get(
                    address_sha1=AddressRef.hash_address(
                        {key: dict_ref[ref_key] for ref_key, key in field_map},
                    ),
                )
            except AddressRef.DoesNotExist:
                instance = AddressRef(
                    address1=dict_address["AddressValidateResponse"]["Address"][
                        "Address2"
                    ],
                    address2=dict_address["AddressValidateResponse"]["Address"][
                        "Address1"
                    ],
                    city=dict_address["AddressValidateResponse"]["Address"]["City"],
                    state=dict_address["AddressValidateResponse"]["Address"]["State"],
                    zip_code=int(
                        dict_address["AddressValidateResponse"]["Address"]["Zip5"],
                    ),
                )
                instance.clean()

            # Finalize the address portion
            finalize_address(instance, is_in_gma, has_connexion)

            # Get the first address in the list of addresses
            # that is not yet processed
            addresses = json.loads(request.session["application_addresses"])
            address = [address for address in addresses if not address["processed"]][0]

            # Mark the address as processed and create a new key on the
            # dictionary for storing the instance.
            address["processed"] = True
            address["instance"] = instance.pk

            # Save the updated list of addresses to the session
            request.session["application_addresses"] = json.dumps(addresses)

            # Check if we need to process any other addresses
            if [address for address in addresses if not address["processed"]]:
                return redirect(reverse("app:address_correction"))

            # Check to see if a address with the type 'eligibility' exists in the
            # request.session['application_addresses'].
            eligibility_addresses = [
                address for address in addresses if address["type"] == "eligibility"
            ]
            mailing_addresses = [
                address for address in addresses if address["type"] == "mailing"
            ]
            if eligibility_addresses:
                try:
                    # Create and save a record for the user's address using
                    # the Address object
                    if mailing_addresses:
                        Address.objects.create(
                            user=request.user,
                            eligibility_address=AddressRef.objects.get(
                                id=eligibility_addresses[0]["instance"],
                            ),
                            mailing_address=AddressRef.objects.get(
                                id=mailing_addresses[0]["instance"],
                            ),
                        )
                    else:
                        Address.objects.create(
                            user=request.user,
                            eligibility_address=AddressRef.objects.get(
                                id=eligibility_addresses[0]["instance"],
                            ),
                            mailing_address=AddressRef.objects.get(
                                id=eligibility_addresses[0]["instance"],
                            ),
                        )
                except IntegrityError:
                    # Update the user's address record if it already exists
                    # (e.g. if the user is updating their address)
                    if mailing_addresses:
                        address = Address.objects.get(user=request.user)
                        address.eligibility_address = AddressRef.objects.get(
                            id=eligibility_addresses[0]["instance"],
                        )
                        address.mailing_address = AddressRef.objects.get(
                            id=mailing_addresses[0]["instance"],
                        )
                    else:
                        address = Address.objects.get(user=request.user)
                        address.eligibility_address = AddressRef.objects.get(
                            id=eligibility_addresses[0]["instance"],
                        )
                        address.mailing_address = AddressRef.objects.get(
                            id=eligibility_addresses[0]["instance"],
                        )

                    # Set the attributes to let pre_save know to save history
                    # address.update_mode = update_mode
                    # address.renewal_mode = renewal_mode

                    address.save()

                if renewal_mode:
                    # Call save_renewal_action after .save() so as not to save
                    # renewal metadata as data updates
                    # save_renewal_action(request, "address")
                    pass

                # Add 'app:address' to `user_completed_pages`
                request.user.user_completed_pages.add(
                    ApplicationPage.objects.get(page_url="app:address"),
                )

                return redirect(reverse("app:household"))
            # We're in update_mode here, so we're only updating the users
            # mailing address. Then redirecting them to their settings page.
            address = Address.objects.get(user=request.user)
            address.mailing_address = AddressRef.objects.get(
                id=mailing_addresses[0]["instance"],
            )

            # Set the attributes to let pre_save know to save history
            # address.update_mode = update_mode

            address.save()
            return redirect(
                f"{reverse('users:detail', kwargs={'pk': request.user.id})}?page_updated=address",
            )

        except (KeyError, TypeError):
            log.warning(
                f"USPS couldn't out the address: {dict_address}",
                function="take_usps_address",
                user_id=request.user.id,
            )
            # HTTP_REFERER sends this button press back to the same page
            # (e.g. removes the button functionality)
            return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="take_usps_address",
            user_id=user_id,
        )
        raise


@method_decorator(login_required, name="dispatch")
class HouseholdFormView(LoginRequiredMixin, EditCollectionView):
    model = Household
    collection_class = HouseholdFormCollection
    template_name = "application/household.html"

    extra_context = None

    def get_initial(self):
        """
        Return initial values for form elements. Note that the dictionary must
        be the same shape as the form collection(s), although not all elements
        need to be defined.

        """
        initial = super().get_initial()

        if initial["members"]:
            return initial
        # If no 'household members' exist, fill the first element with the
        # name of the primary applicant
        return {
            "members": [
                {
                    "person": {
                        "full_name": f"{self.request.user.first_name} {self.request.user.last_name}",
                    },
                },
            ],
        }

    def dispatch(self, *args, **kwargs):
        """Dispatch the view (and set update_mode/renewal_mode)."""

        if self.request.session.get("application_addresses"):
            del self.request.session["application_addresses"]

        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        self.update_mode = self.request.session.get("update_mode", False)
        self.renewal_mode = self.request.session.get("renewal_mode", False)

        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add additional context data to the view."""

        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "title": "Household",
                "update_mode": self.update_mode,
                "renewal_mode": self.renewal_mode,
            },
        )

        return ctx

    def get_object(self, queryset=None):
        """
        Get or create the household object from request attributes, so we don't
        have to pass it in the URL parameters.

        """
        # Use this to convert the user from SimpleLazyObject, as applicable
        user = (
            self.request.user._wrapped
            if hasattr(self.request.user, "_wrapped")
            else self.request.user
        )

        # Return a Household object from the User object
        obj, created = Household.objects.get_or_create(
            user=user,
            # Use `defaults` to set initial values without affecting the 'get'
            # after these are updated with proper values
            defaults={
                "is_updated": False,
                "is_income_verified": False,
                "duration_at_address": "",
                "rent_own": "",
            },
        )
        return obj

    def get(self, request, *args, **kwargs):
        log.debug(
            "Entering function (GET)",
            function="household",
            user_id=request.user.id,
        )

        return super().get(request, *args, **kwargs)

    def form_collection_valid(self, form_collection):
        response = super().form_collection_valid(form_collection)
        return response

    def post(self, request, *args, **kwargs):
        log.debug(
            "Leaving function (POST)",
            function="household",
            user_id=request.user.id,
        )

        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        """Return the URL for a successful POST."""

        # The target changes based on update_mode
        if self.update_mode:
            return f"{reverse('app:user_settings')}?page_updated=household"
        return reverse("app:eligibility_programs")


@login_required()
def programs(request, **kwargs):
    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        renewal_mode = (
            request.session.get("renewal_mode")
            if request.session.get("renewal_mode")
            else False
        )
        if request.method == "POST":
            log.debug(
                "Leaving function (POST)",
                function="programs",
                user_id=request.user.id,
            )

            # This if/else block essentially does the same thing, but the way we
            # delete programs matters for saving data via our signals.py file.
            # The if block actually triggers the signals.py file to save data
            # while the else block does not.
            if renewal_mode:
                # get the user's eligibility programs
                eligibility_programs = EligibilityProgram.objects.filter(
                    user_id=request.user.id,
                )
                # for every program loop through and delete the program
                for program in eligibility_programs:
                    # program.renewal_mode = True
                    program.delete()
            else:
                # In case a user has migrated back to the programs page, clear out their existing
                # eligibility programs and have them start fresh.
                EligibilityProgram.objects.filter(user_id=request.user.id).delete()

            # Serialize POST request
            eligibility_programs = {}
            for key, value in request.POST.items():
                if key == "csrfmiddlewaretoken":
                    continue
                eligibility_programs[key] = value

            # Using the EligibilityProgram model insert multiple rows into the database
            # with the eligibility_programs and the user_id. Each key value in the eligibility_programs is a
            # separate row in the database.
            selected_eligibility_programs = []
            for value in eligibility_programs.values():
                selected_eligibility_programs.append(
                    EligibilityProgram(
                        user_id=request.user.id,
                        program_id=value,
                        # renewal_mode=renewal_mode,
                    ),
                )

            if renewal_mode:
                # save_renewal_action(request, "eligibility_programs")
                pass

            EligibilityProgram.objects.bulk_create(selected_eligibility_programs)

            # Add 'app:programs' to `user_completed_pages`
            request.user.user_completed_pages.add(
                ApplicationPage.objects.get(page_url="app:programs"),
            )

            return redirect(reverse("app:files"))
        log.debug(
            "Entering function (GET)",
            function="programs",
            user_id=request.user.id,
        )

        # Get all of the programs (except the one with identification and where is_active is False) from the application_EligibilityProgramRef table
        # ordered by the friendly_name field acending
        programs = EligibilityProgramRef.objects.filter(
            is_active=True,
        ).order_by(
            "friendly_name",
        )

        return render(
            request,
            "application/programs.html",
            {
                "programs": programs,
                "step": 4,
                "form_page_number": form_page_number,
                "title": "Programs",
                "renewal_mode": renewal_mode,
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="programs",
            user_id=user_id,
        )
        raise


@login_required()
def files(request, **kwargs):
    """
    Determine what files the user needs to upload for their selected programs.

    Variables:
    fileNames - used to name the files in the database and file upload
    fileAmount - number of file uploads per income verified documentation
    """

    try:
        # Check the boolean value of update_mode session var
        # Set as false if session var DNE
        renewal_mode = (
            request.session.get("renewal_mode")
            if request.session.get("renewal_mode")
            else False
        )
        users_programs_without_uploads = get_in_progress_eligiblity_file_uploads(
            request,
        )

        if request.method == "POST":
            log.debug(
                "Leaving function (POST)",
                function="files",
                user_id=request.user.id,
            )

            user_file_upload = EligibilityProgram.objects.get(pk=request.POST["id"])
            form = FileUploadForm(
                request.POST,
                request.FILES,
                instance=user_file_upload,
            )
            if form.is_valid():
                instance = form.save(commit=False)
                fileNames = []
                fileAmount = 0

                # Loop 1: scans files
                # Loop 2: saves file(s) if valid
                for f in request.FILES.getlist("document_path"):
                    file_validated, failure_message_or_file_extension = file_validation(
                        f,
                        request.user.id,
                        calling_function="files",
                    )
                    if not file_validated:
                        users_programs_without_uploads = (
                            get_in_progress_eligiblity_file_uploads(request)
                        )
                        return render(
                            request,
                            "application/files.html",
                            {
                                "message": failure_message_or_file_extension,
                                "form": form,
                                "eligiblity_programs": users_programs_without_uploads,
                                "step": 5,
                                "form_page_number": form_page_number,
                                "title": "Files",
                                "file_upload": json.dumps({"success_status": False}),
                                "renewal_mode": renewal_mode,
                            },
                        )

                for f in request.FILES.getlist("document_path"):
                    fileAmount += 1
                    # instance.renewal_mode = renewal_mode

                    # This allows us to save multiple files under the same
                    # Eligibility Program record. Note that the database is updated
                    # each time this loop is run, plus again for the final save()
                    # afterward
                    instance.document_path.save(
                        pendulum.now(
                            "utc",
                        ).format(
                            f"YYYY-MM-DD[T]HHmmss[Z_{fileAmount}_{f}]",
                        ),
                        f,
                    )
                    fileNames.append(str(instance.document_path))
                    log.debug(
                        f"Eligibility file {instance.document_path} saved successfully",
                        function="files",
                        user_id=request.user.id,
                    )

                # Save the fileNames list as a single document_path string
                instance.document_path = str(fileNames)
                instance.save()

                if fileAmount == 0:
                    log.info(
                        "No Eligibility Program files to upload were found",
                        function="files",
                        user_id=request.user.id,
                    )

                users_programs_without_uploads = (
                    get_in_progress_eligiblity_file_uploads(request)
                )
                if users_programs_without_uploads.count():
                    return render(
                        request,
                        "application/files.html",
                        {
                            "form": form,
                            "eligiblity_programs": users_programs_without_uploads,
                            "step": 5,
                            "form_page_number": form_page_number,
                            "title": "Files",
                            "file_upload": json.dumps({"success_status": True}),
                            "renewal_mode": renewal_mode,
                        },
                    )
                # Once all files have been uploaded, finalize the application
                target_page, session_updates = finalize_application(
                    request.user,
                    renewal_mode=renewal_mode,
                )
                # Update the session vars from the finalize application output
                for key, itm in session_updates.items():
                    request.session[key] = itm

                # Add 'app:files' to `user_completed_pages`
                request.user.user_completed_pages.add(
                    ApplicationPage.objects.get(page_url="app:files"),
                )

                # Redirect to the finalize application target
                return redirect(target_page)

        else:
            log.debug(
                "Entering function (GET)",
                function="files",
                user_id=request.user.id,
            )

            form = FileUploadForm()
            return render(
                request,
                "application/files.html",
                {
                    "form": form,
                    "eligiblity_programs": users_programs_without_uploads,
                    "step": 5,
                    "form_page_number": form_page_number,
                    "title": "Files",
                    "file_upload": json.dumps({"success_status": None}),
                    "renewal_mode": renewal_mode,
                },
            )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="files",
            user_id=user_id,
        )
        raise


@login_required()
def broadcast(request, **kwargs):
    try:
        log.debug(
            "Entering function",
            function="broadcast",
            user_id=request.user.id,
        )

        current_user = request.user
        try:
            broadcast_email(current_user.email)
        except Exception:
            log.exception(
                "There was a problem with sending the email (Sendgrid)",
                function="broadcast",
                user_id=request.user.id,
            )
            # TODO store / save for later: client getting feedback that SendGrid may be down
        phone = str(current_user.phone_number)
        try:
            broadcast_sms(phone)
        except Exception:
            log.exception(
                "Twilio servers may be down",
                function="broadcast",
                user_id=request.user.id,
            )
            # TODO store / save for later: client getting feedback that twilio may be down

        log.info(
            "Application completed successfully",
            function="broadcast",
            user_id=request.user.id,
        )

        # Note in the database when notifications were sent
        current_user.last_action_notification_at = pendulum.now()
        current_user.save()

        return render(
            request,
            "application/broadcast.html",
            {
                "program_string": current_user.email,
                "step": 6,
                "form_page_number": form_page_number,
                "title": "Broadcast",
            },
        )

    # General view-level exception catching
    except Exception:
        try:
            user_id = request.user.id
        except Exception:
            user_id = None
        log.exception(
            "Uncaught view-level exception",
            function="broadcast",
            user_id=user_id,
        )
        raise
