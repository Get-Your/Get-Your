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

from tomlkit import loads
from tomlkit import exceptions as tomlexceptions
from django.core.exceptions import ImproperlyConfigured

from getyour.settings.common_settings import *

# SECURITY WARNING: keep the secret key used in production secret!
# TOML-based secrets module
with open('.prod.deploy', 'r', encoding='utf-8') as f:
    secrets_dict = loads(f.read())

def get_secret(var_name, read_dict=secrets_dict):
    '''Get the secret variable or return explicit exception.'''
    try:
        return read_dict[var_name]
    except tomlexceptions.NonExistentKey:
        error_msg = f"Set the '{var_name}' secrets variable"
        raise ImproperlyConfigured(error_msg)

SECRET_KEY = get_secret('SECRET_KEY')
TWILIO_ACCOUNT_SID = get_secret('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_secret('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = get_secret('TWILIO_NUMBER')
USPS_SID = get_secret('USPS_SID')
DB_USER = get_secret('DB_USER')
DB_PASS = get_secret('DB_PASS')
SENDGRID_API_KEY = get_secret('SENDGRID_API_KEY')
TEMPLATE_ID = get_secret("TEMPLATE_ID")
TEMPLATE_ID_PW_RESET = get_secret("TEMPLATE_ID_PW_RESET")
TEMPLATE_ID_DYNAMIC_EMAIL = get_secret("TEMPLATE_ID_DYNAMIC_EMAIL")
TEMPLATE_ID_RENEWAL = get_secret("TEMPLATE_ID_RENEWAL")
AZURE_ACCOUNT_NAME = get_secret("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = get_secret("AZURE_ACCOUNT_KEY")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.usgovcloudapi.net"
AZURE_CONTAINER = get_secret("AZURE_CONTAINER")
IS_PROD = None  # 'None' implies this is the stage database

# DEBUG moved to Azure App Service environment var (or False, via common_settings)

CSRF_TRUSTED_ORIGINS = [f"https://{x}" for x in get_secret("HOSTS")]
ALLOWED_HOSTS = get_secret("HOSTS")

# Application definitions (outside of common_settings)

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_stage',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
    },
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_stage_analytics',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
    }
}

# Logging modifications
# This uses an Azure App Service environment var
if DEBUG_LOGGING:
    LOGGING['loggers']['app']['level'] = 'DEBUG'

Q_CLUSTER = {
    'name': 'DjangORM',
    'workers': 4,
    # Each worker is constrained to the timeout period
    'timeout': 30,
    # Each worker and the scheduled task itself is constrained to the retry
    # period. At least some scheduled tasks in Get-Your are expected to be long-
    # running because they loop through each user; set this accordingly
    'retry': 21500,     # just under 6 hours
    # The max_attempts parameter is actually a limit for number of *retries*.
    # Appears to only accept positive integer or zero; zero indicates 'infinite'
    'max_attempts': 1,
    'bulk': 10,
    'orm': 'default',
    'catch_up': False,
}
