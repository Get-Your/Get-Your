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

from getyour.settings.common import *
from getyour.settings.common import env

# Read the environment-specific secrets
env.read_env(BASE_DIR.joinpath('.prod.deploy'))

SECRET_KEY = env("SECRET_KEY")
AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY")
AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.usgovcloudapi.net"
AZURE_CONTAINER = env("AZURE_CONTAINER")
IS_PROD = True

# DEBUG moved to Azure App Service environment var (or False, via settings.common)

CSRF_TRUSTED_ORIGINS = [f"https://{x}" for x in env.list("HOSTS")]
ALLOWED_HOSTS = env.list("HOSTS")

# Application definitions (outside of settings.common)

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_prod',
        'USER': env("DB_USER"),
        'PASSWORD': env("DB_PASS"),
        'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
    },
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'getyour_prod_analytics',
        'USER': env("DB_USER"),
        'PASSWORD': env("DB_PASS"),
        'HOST': 'getfoco-postgres-no-vnet.postgres.database.usgovcloudapi.net'
    }
}

# Logging modifications
# This uses an Azure App Service environment var
if DEBUG_LOGGING:
    LOGGING['loggers']['app']['level'] = 'DEBUG'

Q_CLUSTER = {
    'name': 'DjangORM',
    'workers': 4,
    # Each worker is constrained to the timeout period
    'timeout': 30,
    # Each worker and the scheduled task itself is constrained to the retry
    # period. At least some scheduled tasks in Get-Your are expected to be long-
    # running because they loop through each user; set this accordingly
    'retry': 21500,     # just under 6 hours
    # The max_attempts parameter is actually a limit for number of *retries*.
    # Appears to only accept positive integer or zero; zero indicates 'infinite'
    'max_attempts': 1,
    'bulk': 10,
    'orm': 'default',
    'catch_up': False,
}
