import logging

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from log_ext.models import Detail


class DetailAdmin_ext(admin.ModelAdmin):
    list_display = ('colored_msg', 'traceback', 'created_at_format')
    list_display_links = ('colored_msg',)
    list_filter = ('log_level',)
    list_per_page = 10

    def colored_msg(self, instance):
        if instance.level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif instance.level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {color};">{msg}</span>', color=color, msg=instance.msg)

    colored_msg.short_description = 'Message'

    def traceback(self, instance):
        return format_html('<pre><code>{content}</code></pre>', content=instance.trace if instance.trace else '')

    def created_at_format(self, instance):
        return timezone.localtime(instance.created_at).strftime('%Y-%m-%d %X')

    created_at_format.short_description = 'Created at'


admin.site.register(Detail, DetailAdmin_ext)
