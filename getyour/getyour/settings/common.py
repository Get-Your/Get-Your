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

import os
import subprocess
from pathlib import Path

import environ
from django.core.files import File

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# getyour/
APPS_DIR = BASE_DIR / "getyour"
env = environ.Env()

# Read and apply the environment-agnostic secrets
env.read_env(BASE_DIR.joinpath(".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
# Add environment variables optionally set by Azure or in the Docker build.
# These will use the environment var if exists, else the .env file or fallback
# to the defined default
if os.environ.get("DEBUG") is None:
    DEBUG = env.bool("DEBUG", False)
else:
    DEBUG = str(os.environ.get("DEBUG")).lower() == "true"

if os.environ.get("DEBUG_LOGGING") is None:
    DEBUG_LOGGING = env.bool("DEBUG_LOGGING", False)
else:
    DEBUG_LOGGING = str(os.environ.get("DEBUG_LOGGING")).lower() == "true"

# Code version display
try:
    # Try to load the code version from environment vars. Note that the
    # Dockerfile defaults to '', so False is only returned if CODE_VERSION env
    # var DNE
    CODE_VERSION = os.environ.get("CODE_VERSION", False)
    if CODE_VERSION is False:
        # Otherwise, try to find the current Git version directly from the repo.
        # The assumption is that this is part of a Git repo if not built by
        # Docker

        # Run `git describe --tags`
        CODE_VERSION = (
            subprocess.check_output(["git", "describe", "--tags"])
            .decode("ascii")
            .strip()
        )

except Exception:
    # Cannot be found; use blank
    CODE_VERSION = ""

# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "America/Denver"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#internationalization-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#localization-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# For phone number default region setting:
PHONENUMBER_DEFAULT_REGION = "US"

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "getyour.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django.contrib.admin",
]
THIRD_PARTY_APPS = [
    "phonenumber_field",
    "django_q",
    "django_json_widget",
]

LOCAL_APPS = [
    "app",
    "logger",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "app.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "app:login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "getyour.middleware.FirstViewMiddleware",
    "getyour.middleware.ValidRouteMiddleware",
    "getyour.middleware.LoginRequiredMiddleware",
    "getyour.middleware.RenewalModeMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "static/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.joinpath("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "app.context_processors.global_template_variables",
            ],
        },
    },
]

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# MEDIA
# ------------------------------------------------------------------------------
# Media storage and common Azure setting
# Ref https://stackoverflow.com/a/54767932/5438550 for details
# Subdirectory-like prefix to the blob name
AZURE_LOCATION = ""
DEFAULT_FILE_STORAGE = "getyour.settings.custom_azure.AzureMediaStorage"

# Define database routing other than the default
# https://docs.djangoproject.com/en/dev/ref/settings/#database-routers
DATABASE_ROUTERS = ["getyour.routers.LogRouter"]

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(message)s",
            # datefmt is autocreated by Django; it would be ignored here
        },
    },
    "handlers": {
        "db_log": {
            "class": "logger.handlers.DatabaseLogHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {
            "handlers": ["db_log"],
            "level": "INFO",
        },
        # Keep this logger! Even though it's a duplicate of the root logger,
        # the environment-specific settings may reference it
        "app": {
            "handlers": ["db_log"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["db_log"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Get-Your-specific
# ------------------------------------------------------------------------------
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = env("TWILIO_NUMBER")
CONTACT_EMAIL = env("CONTACT_EMAIL")
USPS_KEY = env("USPS_KEY")
USPS_SECRET = env("USPS_SECRET")
SENDGRID_API_KEY = env("SENDGRID_API_KEY")
WELCOME_EMAIL_TEMPLATE = env("WELCOME_EMAIL_TEMPLATE")
PW_RESET_EMAIL_TEMPLATE = env("PW_RESET_EMAIL_TEMPLATE")
RENEWAL_EMAIL_TEMPLATE = env("RENEWAL_EMAIL_TEMPLATE")

# Verify that the file chunk size is greater than the python-magic recommended
# minimum read of 2048 bytes
# (https://github.com/ahupp/python-magic?tab=readme-ov-file#usage)
if File.DEFAULT_CHUNK_SIZE < 2048:
    raise AssertionError(
        "The DEFAULT_CHUNK_SIZE for uploaded files is too small for python-magic to produce a correct identification"
    )

# Increase the maximum upload size in order to allow proper identification
# uploads. Because that page currently tries to upload all files simultaneously,
# the per-page maximum needs to be increased to prevent errors
# As of 2023-08-01:
# the 99th percentile of file sizes was 8.33 MiB
# the 99th percentile for individuals in household was 7.00
# therefore the file payload for the 99th percentile of persons and file
# size: 58.28 MiB
# Use this value + (lots of) overhead

# the largest uploaded file was 43.4 MiB; one file at this size can be
# uploaded
max_upload_size_mib = 100
DATA_UPLOAD_MAX_MEMORY_SIZE = max_upload_size_mib * 1048576
