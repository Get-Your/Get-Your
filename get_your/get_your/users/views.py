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

from allauth.account.views import SignupView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from get_your.users.models import User
from ref.models import ApplicationPage


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["first_name", "last_name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        """
        Get the redirect URL for the now-logged-in user.

        Note that this occurs only if there is no login_required() redirect (
        e.g. this code happens after login_required() resolution).

        """
        # TODO: if a user in mid-renewal, have a case for page/modal to prompt user to continue renewal or go to dashboard
        all_pages = ApplicationPage.objects.order_by("page_order").all()

        completed_pages = self.request.user.user_completed_pages.order_by(
            "page_order",
        ).all()
        if completed_pages.count() > 0:
            first_uncompleted_page = next(
                iter(x for x in all_pages if x not in completed_pages),
            )
        else:
            first_uncompleted_page = ApplicationPage.objects.order_by(
                "page_order",
            ).first()
        # TODO: Need error checking for this
        # TODO: Connect URL parameter to modal advising the user that the app is continuing where they left off
        return f"{reverse(first_uncompleted_page.page_url)}?continue=1"

        # Original value here:
        # return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


class UserSignupView(SignupView):
    template_name = "users/signup.html"

    def post(self, request, *args, **kwargs):
        # Extend post() to add 'users:signup' to `user_completed_pages`
        request.user.user_completed_pages.add(
            ApplicationPage.objects.get(page_url="users:signup"),
        )
        return super().post(request, *args, **kwargs)


signup = UserSignupView.as_view()
