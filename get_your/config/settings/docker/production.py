"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

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

from .base import *  # noqa: F403
from .base import INSTALLED_APPS
from .base import REDIS_URL
from .base import env

# ENV
# ------------------------------------------------------------------------------
# Read the DEV secrets file into env, overwriting any existing vars (there
# shouldn't be any matching variables, but this is in case we have need to have
# environment-specific overwrites).
# Because this is a local environment, some settings are unused and set
# explicity in this file
if READ_DOT_ENV_FILE:
    env.read_env(str(BASE_DIR / ".prod.deploy"), overwrite=True)

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["fcgov.com"])

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Create the Postgres URI from individual parameters in secrets file
DATABASES = {
    "default": env.db(
        # env.db expects a DATABASE_URL environment var; using the 'default'
        # kwarg allows building the connection string here
        default="postgres://{usr}:{pwd}@{hst}:{prt}/{dbn}".format(
            usr=env("POSTGRES_USER"),
            pwd=env("POSTGRES_PASSWORD"),
            hst=env("POSTGRES_HOST"),
            prt=env("POSTGRES_PORT"),
            dbn=env("POSTGRES_DB"),
        ),
    ),
    "monitor": env.db(
        # env.db expects a DATABASE_URL environment var; using the 'default'
        # kwarg allows building the connection string here
        default="postgres://{usr}:{pwd}@{hst}:{prt}/{dbn}".format(
            usr=env("POSTGRES_USER"),
            pwd=env("POSTGRES_PASSWORD"),
            hst=env("POSTGRES_HOST"),
            prt=env("POSTGRES_PORT"),
            dbn=env("MONITOR_DB"),
        ),
    ),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicking memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
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
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

AZURE_ACCOUNT_KEY = env("DJANGO_AZURE_ACCOUNT_KEY")
AZURE_ACCOUNT_NAME = env("DJANGO_AZURE_ACCOUNT_NAME")
AZURE_CONTAINER = env("DJANGO_AZURE_CONTAINER_NAME")
AZURE_CONTAINER_SUFFIX = env("DJANGO_AZURE_CONTAINER_SUFFIX")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}{AZURE_CONTAINER_SUFFIX}"
# STATIC & MEDIA
# ------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "location": "media",
            "overwrite_files": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = f"https://{AZURE_CUSTOM_DOMAIN}/media/"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="Get FoCo <getfoco@fcgov.com>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[Get FoCo] ",
)
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps/sendgrid/
EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
ANYMAIL = {
    "SENDGRID_API_KEY": env("SENDGRID_API_KEY"),
    "SENDGRID_API_URL": env("SENDGRID_API_URL", default="https://api.sendgrid.com/v3/"),
}

# LOGGING MODIFICATIONS
# ------------------------------------------------------------------------------
# Add environment-specific loggers (I don't know if this is the correct
# way to do this)
LOGGING["loggers"].update(
    {
        "django.db.backends": {
            "handlers": ["db_log"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "handlers": ["db_log"],
            "level": "ERROR",
            "propagate": False,
        },
    },
)

# Set logging level to DEBUG
LOGGING["loggers"]["app"]["level"] = "DEBUG"

# Get-Your-specific
# ------------------------------------------------------------------------------
IS_PROD = True
