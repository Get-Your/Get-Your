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
from environ import Env
from datetime import datetime

from getyour.settings.common_settings import *

env = Env()
env.read_env(env_file='.dev.env')

# Below is loading via .env (for Docker purposes)
SECRET_KEY = env("SECRET_KEY")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = env("TWILIO_NUMBER")
USPS_SID = env("USPS_SID")
DB_USER = env("DB_USER")
DB_PASS = env("DB_PASS")
SENDGRID_API_KEY = env('SENDGRID_API_KEY')
TEMPLATE_ID = env("TEMPLATE_ID")
TEMPLATE_ID_PW_RESET = env("TEMPLATE_ID_PW_RESET")
TEMPLATE_ID_DYNAMIC_EMAIL = env("TEMPLATE_ID_DYNAMIC_EMAIL")
BLOB_STORE_NAME = env("BLOB_STORE_NAME")
BLOB_STORE_KEY = env("BLOB_STORE_KEY")
BLOB_STORE_SUFFIX = env("BLOB_STORE_SUFFIX")
USER_FILES_CONTAINER = env("USER_FILES_CONTAINER")
SITE_HOSTNAME = env("HOST")
IS_PROD = False

# SECURITY WARNING: don't run with debug turned on for any live site!
DEBUG = False

CSRF_TRUSTED_ORIGINS = [f"https://{SITE_HOSTNAME}"]
ALLOWED_HOSTS = [SITE_HOSTNAME]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_dev',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': 'getfoco-postgres-dev.postgres.database.usgovcloudapi.net'
    }
}