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
import os
import json
from pathlib import Path
from datetime import datetime
from django.core.exceptions import ImproperlyConfigured

from getyour.settings.common_settings import *

# SECURITY WARNING: keep the secret key used in production secret!
# JSON-based secrets module
with open('secrets_prod.json') as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    '''Get the secret variable or return explicit exception.'''
    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'Set the {0} environment variable'.format(setting)
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
BLOB_STORE_NAME = get_secret("BLOB_STORE_NAME")
BLOB_STORE_KEY = get_secret("BLOB_STORE_KEY")
BLOB_STORE_SUFFIX = get_secret("BLOB_STORE_SUFFIX")
USER_FILES_CONTAINER = get_secret("USER_FILES_CONTAINER")
IS_PROD = True

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = True

# Revert to default (permissive) values when running locally
CSRF_TRUSTED_ORIGINS = []
ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_prod',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
    }
}
