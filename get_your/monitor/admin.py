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
from django.utils import timezone
from django.utils.html import format_html

from .models import LogDetail


class DetailAdmin(admin.ModelAdmin):
    list_display = ("colored_msg", "traceback", "created_at_format")
    list_display_links = ("colored_msg",)
    list_filter = ("log_level",)
    list_per_page = 10

    def colored_msg(self, instance):
        if instance.level in [logging.NOTSET, logging.INFO]:
            color = "green"
        elif instance.level in [logging.WARNING, logging.DEBUG]:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {color};">{msg}</span>',
            color=color,
            msg=instance.msg,
        )

    colored_msg.short_description = "Message"

    def traceback(self, instance):
        return format_html(
            "<pre><code>{content}</code></pre>",
            content=instance.trace if instance.trace else "",
        )

    def created_at_format(self, instance):
        return timezone.localtime(instance.created_at).strftime("%Y-%m-%d %X")

    created_at_format.short_description = "Created at"


admin.site.register(LogDetail, DetailAdmin)
