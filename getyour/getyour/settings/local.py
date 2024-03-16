"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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

from getyour.settings.common import *
from getyour.settings.common import env

# Read the environment-specific secrets
env.read_env(BASE_DIR.joinpath('.env'))

SECRET_KEY = env("SECRET_KEY")
AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.usgovcloudapi.net"
AZURE_CONTAINER = env("AZURE_CONTAINER")
IS_PROD = False

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = True

# Revert to default (permissive) values when running locally
CSRF_TRUSTED_ORIGINS = []
ALLOWED_HOSTS = []

# Application definitions (outside of settings.common)

DB_USER = env("DB_USER")
DB_PASS = env("DB_PASS")
# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_dev',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'localhost'
    },
    # Note that a separate file is needed for proper concurrency
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_logs_dev',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'localhost'
    }
}
# # Database
# # https://docs.djangoproject.com/en/3.1/ref/settings/#databases
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     },
#     # Note that a separate file is needed for proper concurrency
#     'analytics': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db_analytics.sqlite3',
#     }
# }

# Logging modifications - set logging level to DEBUG and overwrite DEBUG_LOGGER
# env var for clarity
LOGGING['loggers']['app']['level'] = 'DEBUG'
DEBUG_LOGGING = True

Q_CLUSTER = {
    'name': 'DjangORM',
    'workers': 4,
    'timeout': 30,
    'bulk': 10,
    'orm': 'default',
    'catch_up': False,
    'sync': True,   # this is required for Windows
}
