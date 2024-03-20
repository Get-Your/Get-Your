import logging

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ngettext

from logger.models import Detail


@admin.register(Detail)
class DetailAdmin(admin.ModelAdmin):
    ordering = ('-id', )
    list_display = ('id', 'created_at_format', 'color_coded_msg', 'traceback')
    list_display_links = ('color_coded_msg', )
    list_filter = ('logger_name', 'log_level', 'has_been_addressed')
    list_per_page = 100

    actions = ('mark_addressed', )

    @admin.action(description="Mark selected as 'addressed'")
    def mark_addressed(self, request, queryset):
        updated = queryset.update(has_been_addressed=True)
        self.message_user(request, ngettext(
            "%d record was successfully marked as 'addressed'.",
            "%d records were successfully marked as 'addressed'.",
            updated,
        ) % updated, messages.SUCCESS)

    def color_coded_msg(self, instance):
        if instance.log_level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif instance.log_level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {color};">{msg}</span>', color=color, msg=instance.message)

    color_coded_msg.short_description = 'Message'

    def traceback(self, instance):
        return format_html('<pre><code>{content}</code></pre>', content=instance.trace if instance.trace else '')

    def created_at_format(self, instance):
        return timezone.localtime(instance.created_at).strftime('%Y-%m-%d %X')

    created_at_format.short_description = 'Created at'
