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
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from app.views import landing, authentication, application, dashboard


urlpatterns = [
    # Landing URLs
    path('', landing.index, name='index'),
    # Available/NotAvailable Digital Equity in your area
    path('quick_available', landing.quick_available, name='quick_available'),
    path('quick_not_available', landing.quick_not_available,
         name='quick_not_available'),
    path('quick_coming_soon', landing.quick_coming_soon, name='quick_coming_soon'),
    path('quick_not_found', landing.quick_not_found, name='quick_not_found'),
    path('programs_info', landing.programs_info, name='programs_info'),
    path('privacy_policy', landing.privacy_policy, name='privacy_policy'),

    # Application URLs
    path('address', application.address, name='address'),
    path('account', application.account, name='account'),
    path('household', application.household, name='household'),
    path('household_members', application.household_members,
         name='household_members'),
    path('programs', application.programs, name='programs'),
    path('address_correction', application.address_correction,
         name='address_correction'),
    path('take_usps_address', application.take_usps_address,
         name='take_usps_address'),
    path('household_definition', application.household_definition,
         name='household_definition'),
    path('get_ready', application.get_ready, name='get_ready'),
    path('files', application.files, name='files'),
    path('broadcast', application.broadcast, name='broadcast'),
    path('notify_remaining', application.notify_remaining, name='notify_remaining'),

    # Dashboard URLs
    path('quick_apply/<str:iq_program>',
         dashboard.quick_apply, name='quick_apply'),
    path('feedback', dashboard.feedback, name='feedback'),
    path('feedback_received', dashboard.feedback_received,
         name="feedback_received"),
    path('dashboard', dashboard.dashboard, name='dashboard'),
    path('qualified_programs', dashboard.qualified_programs,
         name='qualified_programs'),
    path('programs_list', dashboard.programs_list, name='programs_list'),
    path('user_settings', dashboard.user_settings, name='user_settings'),
    path('privacy', dashboard.privacy, name='privacy'),

    # Authentication URLs
    path('login', authentication.login_user, name='login'),
    path("password_reset", authentication.password_reset_request,
         name="password_reset")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
