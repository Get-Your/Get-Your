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

from django.urls import path

from app import views

from .admin import views as admin_views

urlpatterns = [
    # Landing URLs
    path(
        "",
        views.index,
        name="index",
        kwargs={"allow_direct_user": True},
    ),
    # Available/NotAvailable Digital Equity in your area
    path(
        "quick_available",
        views.quick_available,
        name="quick_available",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "quick_not_available",
        views.quick_not_available,
        name="quick_not_available",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "quick_coming_soon",
        views.quick_coming_soon,
        name="quick_coming_soon",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "quick_not_found",
        views.quick_not_found,
        name="quick_not_found",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "programs_info",
        views.programs_info,
        name="programs_info",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "privacy_policy",
        views.privacy_policy,
        name="privacy_policy",
        kwargs={"allow_direct_user": True},
    ),
    # Application URLs
    path(
        "address",
        views.address,
        name="address",
        kwargs={"allow_direct_user": False},
    ),
    # path(
    #     "account",
    #     views.account,
    #     name="account",
    #     kwargs={"allow_direct_user": True},
    # ),
    path(
        "household",
        views.household,
        name="household",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "household_members",
        views.household_members,
        name="household_members",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "programs",
        views.programs,
        name="programs",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "address_correction",
        views.address_correction,
        name="address_correction",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "take_usps_address",
        views.take_usps_address,
        name="take_usps_address",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "household_definition",
        views.household_definition,
        name="household_definition",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "get_ready",
        views.get_ready,
        name="get_ready",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "files",
        views.files,
        name="files",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "broadcast",
        views.broadcast,
        name="broadcast",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "notify_remaining",
        views.notify_remaining,
        name="notify_remaining",
        kwargs={"allow_direct_user": False},
    ),
    # # Authentication URLs
    # path(
    #     "login",
    #     authentication.login_user,
    #     name="login",
    #     kwargs={"allow_direct_user": True},
    # ),
    # path(
    #     "password_reset",
    #     authentication.password_reset_request,
    #     name="password_reset",
    #     kwargs={"allow_direct_user": False},
    # ),
    # Custom admin URLs
    path(
        "app_admin/view_blob/<path:blob_name>",
        admin_views.view_blob,
        name="admin_view_blob",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "app_admin/add_elig_program/<int:user_id>",
        admin_views.add_elig_program,
        name="admin_add_elig_program",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "app_admin/view_changes",
        admin_views.view_changes,
        name="admin_view_changes",
        kwargs={"allow_direct_user": False},
    ),
]
