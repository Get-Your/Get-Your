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
AZURE_ACCOUNT_NAME = get_secret("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = get_secret("AZURE_ACCOUNT_KEY")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.usgovcloudapi.net"
AZURE_CONTAINER = get_secret("AZURE_CONTAINER")
IS_PROD = True

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = True

# ANDREW: Make sure to change this later!
ALLOWED_HOSTS = ["*", "192.168.0.15"]
# Revert to default (permissive) values when running locally
CSRF_TRUSTED_ORIGINS = []

# Application definition

# As of 2023-08-01
    # the 99th percentile of file sizes was 8.33 MiB
    # the 99th percentile for individuals in household was 7.00
    # therefore the file payload for the 99th percentile of persons and file
    # size: 58.28 MiB
    # Use this value + (lots of) overhead

    # the largest uploaded file was 43.4 MiB; one file at this size can be
    # uploaded
max_upload_size_mib = 100
DATA_UPLOAD_MAX_MEMORY_SIZE = max_upload_size_mib*1048576

INSTALLED_APPS = [
    'django.contrib.admin',  # NOTE: may just be able to stop admin stuff in settings.py
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'app',
    'phonenumber_field',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # add whitenoise
    'getyour.middleware.RenewalModeMiddleware',
]

ROOT_URLCONF = 'getyour.urls'
AUTH_USER_MODEL = "app.User"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, '..', 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app.context_processors.global_template_variables',
            ],
        },
    },
]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

WSGI_APPLICATION = 'getyour.wsgi.application'


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
