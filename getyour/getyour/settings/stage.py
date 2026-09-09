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
env.read_env(BASE_DIR.joinpath(".prod.deploy"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
# DEBUG moved to Azure App Service environment var (or False, via settings.common)
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("HOSTS")
CSRF_TRUSTED_ORIGINS = [f"https://{x}" for x in env.list("HOSTS")]

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
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-name
SESSION_COOKIE_NAME = "__Secure-sessionid"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-name
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# Log out on browser close
# https://docs.djangoproject.com/en/dev/ref/settings/#session-expire-at-browser-close
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Expire the session cookie (force re-login) at 6 hours (in seconds)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-age
SESSION_COOKIE_AGE = 6 * 60 * 60

AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY")
AZURE_ENDPOINT_SUFFIX = "core.usgovcloudapi.net"
AZURE_CONTAINER = env("AZURE_CONTAINER")

# Get-Your-specific
# ------------------------------------------------------------------------------
# IS_PROD == None implies this is the `stage` database
IS_PROD = None

# Logging modifications
# This uses an Azure App Service environment var
if DEBUG_LOGGING:
    LOGGING["loggers"]["app"]["level"] = "DEBUG"

# Define the django-q cluster
Q_CLUSTER = {
    "name": "DJRedis",
    "workers": 4,
    "timeout": 30,
    # Limit the number of retries
    "max_attempts": 1,
    "bulk": 10,
    "django_redis": "default",
    "catch_up": False,
}
