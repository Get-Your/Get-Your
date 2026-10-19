"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2026

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

from .common import *
from .common import env
from .common import INSTALLED_APPS
from .common import MIDDLEWARE

# ENV
# ------------------------------------------------------------------------------
# Read the DEV secrets file into env, overwriting any existing vars (there
# shouldn't be any matching variables, but this is in case we have need to have
# environment-specific overwrites).
env.read_env(BASE_DIR.joinpath(".prod.env"))

# GENERAL
# ------------------------------------------------------------------------------
# SECURITY WARNING: don't run with debug turned on for any live site!
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("SECRET_KEY")
# Revert to default (permissive) values when running locally
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Create the Postgres URI from individual parameters in secrets file
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "getyour_stage",
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASS"),
        "HOST": env("DB_HOST"),
    },
    "analytics": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "getyour_stage_analytics",
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASS"),
        "HOST": env("DB_HOST"),
    },
}

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY")
AZURE_ENDPOINT_SUFFIX = "core.usgovcloudapi.net"
AZURE_CONTAINER = env("AZURE_CONTAINER")

# Get-Your-specific
# ------------------------------------------------------------------------------
# IS_PROD == None implies this is the `stage` database
IS_PROD = None

# Logging modifications - set logging level to DEBUG and overwrite DEBUG_LOGGER
# env var for clarity
LOGGING["loggers"]["app"]["level"] = "DEBUG"
DEBUG_LOGGING = True
