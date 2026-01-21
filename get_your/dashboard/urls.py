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

from dashboard import views

urlpatterns = [
    path(
        "quick_apply/<str:iq_program>",
        views.quick_apply,
        name="quick_apply",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "feedback",
        views.feedback,
        name="feedback",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "feedback_received",
        views.feedback_received,
        name="feedback_received",
        kwargs={"allow_direct_user": False},
    ),
    path(
        "",
        views.dashboard,
        name="dashboard",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "account_overview",
        views.account_overview,
        name="account_overview",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "account_settings",
        views.account_settings,
        name="account_settings",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "account_programs",
        views.account_programs,
        name="account_programs",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "qualified_programs",
        views.qualified_programs,
        name="qualified_programs",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "programs_list",
        views.programs_list,
        name="programs_list",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "user_settings",
        views.user_settings,
        name="user_settings",
        kwargs={"allow_direct_user": True},
    ),
    path(
        "privacy",
        views.privacy,
        name="privacy",
        kwargs={"allow_direct_user": True},
    ),
    # HTMX dashboard modal
    path(
        "apply_now_modal",
        views.apply_now_modal,
        name="apply_now_modal",
        kwargs={"allow_direct_user": False},
    ),
]
