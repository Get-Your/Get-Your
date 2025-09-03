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

from django.contrib import admin
from logger.wrappers import LoggerWrapper

from .models import Feedback

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


class FeedbackAdmin(admin.ModelAdmin):
    search_fields = ("feedback_comments",)
    list_display = list_display_links = ("created", "star_rating")
    list_filter = ("star_rating",)
    ordering = ("-created",)
    date_hierarchy = "created"

    list_per_page = 100

    # Define all possible fields and set them as readonly
    all_possible_fields = readonly_fields = [
        "created",
        "star_rating",
        "feedback_comments",
    ]

    def has_add_permission(self, request, obj=None):
        # Adding directly from the admin panel is disallowed for everyone
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting is disallowed for everyone
        return False

    def get_changelist(self, request, **kwargs):
        # Log entrance to this changelist. This attempts to track called
        # functions
        log.debug(
            "Entering admin changelist",
            function="FeedbackAdmin",
            user_id=request.user.id,
        )

        return super().get_changelist(request, **kwargs)

    def get_fields(self, request, obj=None):
        """
        Return fields based on whether object exists (new or existing).

        Existing addresses can only update is_city_covered, when applicable.
        New addresses can only enter the address information itself.

        """

        # Log entrance to this change page. This attempts to track called
        # functions
        log.debug(
            "Entering admin change page",
            function="FeedbackAdmin",
            user_id=request.user.id,
        )

        return self.all_possible_fields


# Register the models
admin.site.register(Feedback, FeedbackAdmin)
