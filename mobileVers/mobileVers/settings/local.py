"""
Django settings for mobileVers project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


import json

from django.core.exceptions import ImproperlyConfigured

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# JSON-based secrets module
with open('secrets.json') as f:
    secrets = json.loads(f.read())
def get_secret(setting, secrets=secrets):
    '''Get the secret variable or return explicit exception.'''
    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'Set the {0} environment variable'.format(setting)
        raise ImproperlyConfigured(error_msg)

SECRET_KEY = get_secret('SECRET_KEY')
TWILIO_ACCOUNT_SID = get_secret('TWILIO_ACCOUNT_SID') #os.getenv("TWILIO_ACCOUNT_SID") 
TWILIO_AUTH_TOKEN = get_secret('TWILIO_AUTH_TOKEN') #os.getenv("TWILIO_AUTH_TOKEN") 
TWILIO_NUMBER = get_secret('TWILIO_NUMBER') #os.getenv("TWILIO_NUMBER")
USPS_SID = get_secret('USPS_SID') #os.getenv("USPS_ACCOUNT_SID") 
POSTGRESQLPW = get_secret('POSTGRESQLPW') #os.getenv("POSTGRESQLPW")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ANDREW: Make sure to change this later!
ALLOWED_HOSTS = ["*", "192.168.0.15"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin', # NOTE: may just be able to stop admin stuff in settings.py
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    'application',
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
]

ROOT_URLCONF = 'mobileVers.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'mobileVers.wsgi.application'
AUTH_USER_MODEL = "application.User" 
# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# ANDREW: Add Azure stuff here
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


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

TIME_ZONE = 'EST'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# For phone number default region setting:
PHONENUMBER_DEFAULT_REGION = 'US'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
# CSS files
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

#added media path for file uploads
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'