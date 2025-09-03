from django import template
from django.contrib.admin.templatetags import admin_modify

register = template.Library()

@register.inclusion_tag('admin/custom_submit_line.html', takes_context=True)
def custom_submit_row(context):
    """
    Pull in and run the Django admin submit_row templatetag for use with the 
    custom_submit_line template.

    """

    ctx = admin_modify.submit_row(context)
    return ctx