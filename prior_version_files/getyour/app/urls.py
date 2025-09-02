"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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
from app.admin import views as admin_views
from app.views import landing, authentication, application, dashboard


urlpatterns = [
    # Landing URLs
    path(
        '',
        landing.index,
        name='index',
        kwargs={'allow_direct_user': True},
     ),

    # Available/NotAvailable Digital Equity in your area
    path(
        'quick_available',
        landing.quick_available,
        name='quick_available',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'quick_not_available',
        landing.quick_not_available,
        name='quick_not_available',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'quick_coming_soon',
        landing.quick_coming_soon,
        name='quick_coming_soon',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'quick_not_found',
        landing.quick_not_found,
        name='quick_not_found',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'programs_info',
        landing.programs_info,
        name='programs_info',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'privacy_policy',
        landing.privacy_policy,
        name='privacy_policy',
        kwargs={'allow_direct_user': True},
     ),

    # Application URLs
    path(
        'address',
        application.address,
        name='address',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'account',
        application.account,
        name='account',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'household',
        application.household,
        name='household',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'household_members',
        application.household_members,
        name='household_members',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'programs',
        application.programs,
        name='programs',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'address_correction',
        application.address_correction,
        name='address_correction',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'take_usps_address',
        application.take_usps_address,
        name='take_usps_address',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'household_definition',
        application.household_definition,
        name='household_definition',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'get_ready',
        application.get_ready,
        name='get_ready',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'files',
        application.files,
        name='files',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'broadcast',
        application.broadcast,
        name='broadcast',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'notify_remaining',
        application.notify_remaining,
        name='notify_remaining',
        kwargs={'allow_direct_user': False},
     ),

    # Dashboard URLs
    path(
        'quick_apply/<str:iq_program>',
        dashboard.quick_apply,
        name='quick_apply',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'feedback',
        dashboard.feedback,
        name='feedback',
        kwargs={'allow_direct_user': False},
     ),
    path(
        'feedback_received',
        dashboard.feedback_received,
        name="feedback_received",
        kwargs={'allow_direct_user': False},
     ),
    path(
        'dashboard',
        dashboard.dashboard,
        name='dashboard',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'qualified_programs',
        dashboard.qualified_programs,
        name='qualified_programs',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'programs_list',
        dashboard.programs_list,
        name='programs_list',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'user_settings',
        dashboard.user_settings,
        name='user_settings',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'privacy',
        dashboard.privacy,
        name='privacy',
        kwargs={'allow_direct_user': True},
     ),

    # Authentication URLs
    path(
        'login',
        authentication.login_user,
        name='login',
        kwargs={'allow_direct_user': True},
     ),
    path(
        'password_reset',
        authentication.password_reset_request,
        name='password_reset',
        kwargs={'allow_direct_user': False},
     ),

    # Custom admin URLs
    path(
        'app_admin/view_blob/<path:blob_name>',
        admin_views.view_blob,
        name='admin_view_blob',
        kwargs={'allow_direct_user': False},
    ),
    path(
        'app_admin/add_elig_program/<int:user_id>',
        admin_views.add_elig_program,
        name='admin_add_elig_program',
        kwargs={'allow_direct_user': False},
    ),
    path(
        'app_admin/view_changes',
        admin_views.view_changes,
        name='admin_view_changes',
        kwargs={'allow_direct_user': False},
    ),

    # HTMX dashboard modal
    path(
        'apply_now_modal',
        dashboard.apply_now_modal,
        name='apply_now_modal',
        kwargs={'allow_direct_user': False},
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
