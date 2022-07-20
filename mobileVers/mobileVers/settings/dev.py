"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version
"""
"""
Django settings for mobileVers project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
from environ import Env
from datetime import datetime
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()

env.read_env(env_file='.env') 
import json

from django.core.exceptions import ImproperlyConfigured

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# JSON-based secrets module
'''with open('secrets.json') as f:
    secrets = json.loads(f.read())
def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'Set the {0} environment variable'.format(setting)
        raise ImproperlyConfigured(error_msg)'''


#Below is loading via locally
#SECRET_KEY = get_secret('SECRET_KEY')
#TWILIO_ACCOUNT_SID = get_secret('TWILIO_ACCOUNT_SID') #os.getenv("TWILIO_ACCOUNT_SID") 
#TWILIO_AUTH_TOKEN = get_secret('TWILIO_AUTH_TOKEN') #os.getenv("TWILIO_AUTH_TOKEN") 
#TWILIO_NUMBER = get_secret('TWILIO_NUMBER') #os.getenv("TWILIO_NUMBER")
#USPS_SID = get_secret('USPS_SID') #os.getenv("USPS_ACCOUNT_SID") 
#POSTGRESQLPW = get_secret('POSTGRESQLPW') #os.getenv("POSTGRESQLPW")
#SENDGRID_API_KEY = get_secret('SENDGRID_API_KEY')
#TEMPLATE_ID = get_secret("TEMPLATE_ID")


#Below is loading via .env (for Docker purposes)
SECRET_KEY = env("SECRET_KEY") 
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID") 
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN") 
TWILIO_NUMBER = env("TWILIO_NUMBER")
USPS_SID = env("USPS_SID") 
POSTGRESQLPW = env("POSTGRESQLPW")
SENDGRID_API_KEY = env('SENDGRID_API_KEY')
TEMPLATE_ID = env("TEMPLATE_ID")
TEMPLATE_ID_PW_RESET = env("TEMPLATE_ID_PW_RESET")
TEMPLATE_ID_DYNAMIC_EMAIL = env("TEMPLATE_ID_DYNAMIC_EMAIL")
ACCOUNT_NAME = env("ACCOUNT_NAME")
ACCOUNT_KEY = env("ACCOUNT_KEY")
FILESTORE_ENDPOINT_SUFFIX = env("FILESTORE_ENDPOINT_SUFFIX")
CONTAINER_NAME = env("CONTAINER_NAME")+'dev'
IS_PROD = False

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = True

# ANDREW: Make sure to change this later!
ALLOWED_HOSTS = ["*", "192.168.0.15","localhost"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'dashboard',
    'application',
    'phonenumber_field',
    'crispy_forms'
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', #add whitenoise
]

ROOT_URLCONF = 'mobileVers.urls'
AUTH_USER_MODEL = "application.User" 

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

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

WSGI_APPLICATION = 'mobileVers.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.postgresql',
         'NAME': 'getfoco_dev',
         'USER': 'getfocoadmin',
         'PASSWORD': POSTGRESQLPW,
         'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
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


str = str((datetime.now().time()))
logFileName = str.replace(":", "_")
LOGGING = { 
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },  
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/' + logFileName + '.log', 
            'when': 'midnight', # this specifies the interval
            'interval': 1, # defaults to 1, only necessary for other values 
            'backupCount': 100, # how many backup file to keep, 10 days
            'formatter': 'verbose',
        },

    },  
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        '': {
            'handlers': ['file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        }
    },  
}