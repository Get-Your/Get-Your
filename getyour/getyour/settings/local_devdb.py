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
import re

from getyour.settings.common import *
from getyour.settings.common import env

# Read the environment-specific secrets
env.read_env(BASE_DIR.joinpath('.dev.env'))

SECRET_KEY = env("SECRET_KEY")
AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.windows.net"
AZURE_CONTAINER = env("AZURE_CONTAINER")
BLOBVIEWER_ORIGIN = env("BLOBVIEWER_ORIGIN")
IS_PROD = False

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = True

# Revert to default (permissive) values when running locally
CSRF_TRUSTED_ORIGINS = []
ALLOWED_HOSTS = []

# Throw exception if BLOBVIEWER_ORIGIN scheme is not included. An excluded
# scheme will load the file on the current domain, which is unwanted
if not re.match(r'https?://', BLOBVIEWER_ORIGIN):
    raise AttributeError("BLOBVIEWER_ORIGIN must include scheme (http(s)://)")

# Application definitions (outside of settings.common)

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_dev',
        'USER': env("DB_USER"),
        'PASSWORD': env("DB_PASS"),
        'HOST': 'getfoco-postgres-dev.postgres.database.usgovcloudapi.net'
    },
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_dev_analytics',
        'USER': env("DB_USER"),
        'PASSWORD': env("DB_PASS"),
        'HOST': 'getfoco-postgres-dev.postgres.database.usgovcloudapi.net'
    }
}

# Logging modifications - set logging level to DEBUG and overwrite DEBUG_LOGGER
# env var for clarity
LOGGING['loggers']['app']['level'] = 'DEBUG'
LOGGING['loggers']['blobviewer']['level'] = 'DEBUG'
DEBUG_LOGGING = True
