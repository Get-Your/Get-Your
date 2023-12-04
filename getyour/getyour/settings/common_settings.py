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
from pathlib import Path
import pendulum

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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
    'log',
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
STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')

# Media storage and common Azure setting
# Ref https://stackoverflow.com/a/54767932/5438550 for details
AZURE_LOCATION = ""  # Subdirectory-like prefix to the blob name
DEFAULT_FILE_STORAGE = 'getyour.settings.custom_azure.AzureMediaStorage'

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
            'class': 'log.handlers.DatabaseLogHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        '': {
            'handlers': ['db_log'],
            'level': 'INFO',
        },
        'app': {
            'handlers': ['db_log'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['db_log'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
