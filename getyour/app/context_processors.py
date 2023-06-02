import os
import importlib


def global_template_variables(request):
    """These are context variables that are available to all templates"""

    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
    data = {}
    try:
        django_settings = importlib.import_module(settings_module)
        data['is_prod'] = django_settings.IS_PROD
        return data
    except ImportError:
        data['is_prod'] = True
