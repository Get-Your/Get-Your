from django.conf import settings

def global_template_variables(request):
    """These are context variables that are available to all templates"""

    data = {
        'is_prod': settings.IS_PROD,
        'code_version': settings.CODE_VERSION,
    }
    return data
