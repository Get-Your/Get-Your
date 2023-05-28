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
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('address', views.address, name='address'),
    path('account', views.account, name='account'),
    path('household', views.household, name='household'),
    path('household_members', views.household_members, name='household_members'),
    path('programs', views.programs, name='programs'),

    # Available/NotAvailable Digital Equity in your area
    path('not_available', views.not_available, name='not_available'),
    path('quick_available', views.quick_available, name='quick_available'),
    path('quick_not_available', views.quick_not_available,
         name='quick_not_available'),
    path('quick_coming_soon', views.quick_coming_soon, name='quick_coming_soon'),
    path('quick_not_found', views.quick_not_found, name='quick_not_found'),
    path('address_correction', views.address_correction, name='address_correction'),
    path('take_usps_address', views.take_usps_address, name='take_usps_address'),

    # Create the IQ Program Quick Apply Page that has a parameter for the iq_program
    path('quick_apply/<str:iq_program>',
         views.quick_apply, name='quick_apply'),
    path('privacy_policy', views.privacy_policy, name='privacy_policy'),
    path('household_definition', views.household_definition,
         name='household_definition'),
    path('get_ready', views.get_ready, name='get_ready'),

    path('feedback', views.feedback, name='feedback'),
    path('files', views.files, name='files'),
    path('login', views.login_user, name='login'),
    path('broadcast', views.broadcast, name='broadcast'),
    path('feedback_received', views.feedback_received, name="feedback_received"),
    path('notify_remaining', views.notify_remaining, name='notify_remaining'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('qualified_programs', views.qualified_programs, name='qualified_programs'),
    path('programs_list', views.programs_list, name='programs_list'),
    path('programs_info', views.programs_info, name='programs_info'),
    path('user_settings', views.user_settings, name='user_settings'),
    path("password_reset", views.password_reset_request, name="password_reset")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
