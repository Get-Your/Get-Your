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
import environ
import os
from pathlib import Path
import subprocess

env = environ.Env()

# Build paths inside the project like this: BASE_DIR.joinpath('subdir')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read and apply the environment-agnostic secrets
env.read_env(BASE_DIR.joinpath('.env'))

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = env("TWILIO_NUMBER")
USPS_SID = env("USPS_SID")
SENDGRID_API_KEY = env("SENDGRID_API_KEY")
WELCOME_EMAIL_TEMPLATE = env("WELCOME_EMAIL_TEMPLATE")
PW_RESET_EMAIL_TEMPLATE = env("PW_RESET_EMAIL_TEMPLATE")
RENEWAL_EMAIL_TEMPLATE = env("RENEWAL_EMAIL_TEMPLATE")

# Add environment variables optionally set by Azure or in the Docker build.
# These will use the environment var if exists, else the .env file or fallback
# to the defined default
if os.environ.get("DEBUG") is None:
    DEBUG = env.bool("DEBUG", False)
else:
    DEBUG = str(os.environ.get("DEBUG")).lower() == 'true'

if os.environ.get("DEBUG_LOGGING") is None:
    DEBUG_LOGGING = env.bool("DEBUG_LOGGING", False)
else:
    DEBUG_LOGGING = str(os.environ.get("DEBUG_LOGGING")).lower() == 'true'

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
        CODE_VERSION = subprocess.check_output(
            ['git', 'describe', '--tags']
        ).decode('ascii').strip()
        
except Exception:
    # Cannot be found; use blank
    CODE_VERSION = ''

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
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'app',
    'phonenumber_field',
    'logger',
    'django_q',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'getyour.middleware.FirstViewMiddleware',
    'getyour.middleware.ValidRouteMiddleware',
    'getyour.middleware.LoginRequiredMiddleware',
    'getyour.middleware.RenewalModeMiddleware',
]

# Session management
# Log out on browser close
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Expire the session cookie (force re-login) at 6 hours (in seconds)
SESSION_COOKIE_AGE = 6*60*60

ROOT_URLCONF = 'getyour.urls'
AUTH_USER_MODEL = "app.User"
LOGIN_URL = 'app:login'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.joinpath('templates')
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

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

WSGI_APPLICATION = 'getyour.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/
LANGUAGE_CODE = 'en-us'

# USE_TZ means that all timestamps are timezone-aware, and since the backend db
# is also timezone-aware, TIME_ZONE doesn't really matter for current use cases
USE_TZ = True
TIME_ZONE = 'America/Denver'

USE_I18N = True

USE_L10N = True

# For phone number default region setting:
PHONENUMBER_DEFAULT_REGION = 'US'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.joinpath('static')

# Media storage and common Azure setting
# Ref https://stackoverflow.com/a/54767932/5438550 for details
AZURE_LOCATION = ""  # Subdirectory-like prefix to the blob name
DEFAULT_FILE_STORAGE = 'getyour.settings.custom_azure.AzureMediaStorage'

# Define database routing other than the default
DATABASE_ROUTERS = ['getyour.routers.LogRouter']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': "%(message)s",
            # datefmt is autocreated by Django; it would be ignored here
        },
    },
    'handlers': {
        'db_log': {
            'class': 'logger.handlers.DatabaseLogHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        '': {
            'handlers': ['db_log'],
            'level': 'INFO',
        },
        # Keep this logger! Even though it's a duplicate of the root logger,
        # the environment-specific settings may reference it
        'app': {
            'handlers': ['db_log'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['db_log'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
