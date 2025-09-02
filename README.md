# Get-Your

Platform for the universal online application for income-qualified programs

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: GPLv3

> ![CAUTION]
> Note that the following is specific to 'Get FoCo', the City of Fort Collins implementation of the Get-Your platform.

# Table of Contents
1. [Get FoCo](#get-foco)
1. [Running the App](#running-the-app)
1. [Development and Deployment](#development-and-deployment)
    1. [manage.py](#managepy)
    1. [Local Development](#local-development)
    1. [Hybrid Development](#hybrid-development)
    1. [Deployment](#deployment)
        1. [Major-Version Deployment](#major-version-deployment)
        1. [Minor or Patch Deployment](#minor-or-patch-deployment)
        1. [Deploy Django for Production](#deploy-django-for-production)
1. [App Secrets](#app-secrets)
1. [Azure App Service Frontend](#azure-app-service-frontend)
    1. [App Service Plan](#app-service-plan)
    1. [Web App](#web-app)
1. [Azure File Store Backend](#azure-file-store-backend)
    1. [File Store Setup Description](#file-store-setup-description)
1. [Azure Database Backend](#azure-database-backend)
    1. [Database Setup Summary](#database-setup-summary)
    1. [Database Setup Description](#database-setup-description)
    1. [Database Administration](#database-administration)
        1. [Connectivity](#connectivity)
        1. [Creating a Database](#creating-a-database)
        1. [Transferring Between Databases](#transferring-between-databases)
        1. [Set Up Database Users](#set-up-database-users)
1. [Email Settings](#email-settings)
1. [Phone Settings](#phone-settings)
    1. [Sending SMS](#sending-sms)
    1. [Call-Forwarding](#call-forwarding)
        1. [Call-Forwarding Setup](#call-forwarding-setup)
    1. [Call-Forwarding Configuration](#call-forwarding-configuration)
1. [Request a Consultation](#request-a-consultation)
1. [Appendix](#appendix)
    1. [Database Administration Tools](#database-administration-tools)
        1. [Delete User](#delete-user)

# Running the App
This app runs on the Django web framework. Unless otherwise noted, the following commands must be run from the 'platform' directory within this repo.

To run for the first time, a local instance is recommended. To get started, copy the `manage.py` file, paste it as something like `manage_local.py` (see the [manage.py](#managepy) sections for details), then modify the app to use a local environment by changing the line beginning with `os.environ.set...` to 

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobileVers.settings.local')

Next, copy/paste or rename `secrets.xxx.toml.template` as `secrets.dev.toml`. There's no need to set variables for the initial run.

Once the settings have been accounted for, finalize Python setup by [creating a virtual environment](https://docs.python.org/3.9/library/venv.html) (optional, but recommended) and installing dependencies.

On **Ubuntu only**, run the following to match the `libmagic1` dependency installed in the Docker container

    apt-get install libmagic1

On **Windows only**, run

    python3 -m pip install python-magic-bin~=0.4

> If `magic` still isn't working, follow the instructions at https://github.com/pidydx/libmagicwin64.

On either platform, finish by installing all other dependencies

    python3 -m pip install -r requirements.txt

Run the following to create the SQLite database and populate it with the database schema and sample data (coming soon - see https://github.com/Get-Your/Get-Your/issues/63).
> Each database migration must be run separately.

    python3 manage_local.py migrate
    python3 manage_local.py migrate --database=<analytics_database>
    python3 manage_local.py runserver

# Development and Deployment
This app uses files in the `settings/` directory for its environment settings. There are three categories of use cases:

Fully-local development (see [Local Development](#local-development)):
- `local.py`

Local development with remote database (see [Hybrid Development](#hybrid-development)):
- Any file not explicitly named elsewhere in this section (usually named `*local_*.py`)

Deployment (see [Deployment](#deployment)):
- `dev.py`
- `production.py`

## manage.py
The development and production Git branches are set up for deployment such that Django's automatically-created management utility (`manage.py`) points to `settings.dev` in the `dev` branch and `settings.production` in the `main` branch. The `manage.py` designation should not be changed; the Docker build process reads `manage.py`, which means the Git branch can be used as a proxy for the deployment environment.

A local clone of `manage.py` should instead be used for development, where the `settings` module can be updated as needed. This `.py` file can be named with any string before or after 'manage' and be ignored by Git; `manage_local.py` will be referenced in this document.

## Local Development
Local development is completely on the developer's computer. The Django app will be run via 

    python3 manage_local.py runserver
    
(see the [manage.py](#managepy) section on using `manage_local.py` instead of the typical `manage.py`) or

    launch.json

and database operations/migrations will apply to SQLite database files in the repo folder (which will be created if they don't exist). The SQLite databases will be ignored by Git commits.

Local development uses `secrets.dev.toml` for [app secrets](#app-secrets). The SQLite database configuration is hardcoded in `local.py`, so associated variables must exist but won't be used.

## Hybrid Development
Hybrid development is for running the webapp locally on the developer's computer and connecting to a remote database for testing or migrating changes. The Django app will be run via

    python3 manage_local.py runserver
    
(see the [manage.py](#managepy) section on using `manage_local.py` instead of the typical `manage.py`) or

    launch.json

and database operations/migrations will apply to the target remote database.

The primary benefit of this is that these `*local_*.py` scripts have

    DEBUG = True

so that full error messages are displayed on the webpage, rather than the minimal error messaging displayed on the live site.

> Note that `DEBUG` must *always* be set to `False` when the site is viewable on the web.

Hybrid development uses `secrets.dev.toml` and `secrets.prod.toml` for DEV and STAGE/PROD [app secrets](#app-secrets) (respectively).

> Note that **all** migrations must be run via `local_devdb.py` or `caution_local_proddb.py` settings using the privileged database user (summarized in the [database setup](#database-setup-summary)).

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy get_your

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

## Deployment
> ![NOTE]
> Soon, the cookiecutter deployment plan will be implemented here:
>
> ### Docker
> See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).

Deployment consists of building and pushing the Docker container, then pulling into the Azure [Web App](#web-app). Get FoCo is set up for the following:

- DEV
  - The container is manually built and pushed to Docker Hub
  - The DEV Web App has a webhook to pull the `dev` tag whenever it's updated
- STAGE
  - TODO: When the `main` branch is manually pulled into a repo in the private City of Fort Collins Github organization, a Github Action builds and pushes the container to Docker Hub using the latest Git tag and also the `prod` container tag
  - The STAGE Web App has a webhook to pull the `prod` tag whenever it's updated
- PROD
  - PROD is manually swapped from STAGE only after STAGE has been verified

Deployment uses `.dev.deploy` and `.prod.deploy` for DEV and STAGE/PROD [app secrets](#app-secrets) (respectively). There are select environment variables using by Django outside of these files that are stored in Settings > Configuration of each App Service slot in the Azure Portal. These are stored as [deployment slot settings](https://learn.microsoft.com/en-us/azure/app-service/deploy-staging-slots?tabs=portal#which-settings-are-swapped), meaning they are specific to their deployment slot and don't get swapped with the rest of the app. These include:

- `DEBUG_LOGGING`: specifies whether logging uses the 'DEBUG' level or not. If False, the 'INFO' log level will be used instead. This is generally False for PROD and True for STAGE and DEV.

Use the following sections as guidance for deployment (additional steps may be required based on the updates). Generic commands are included for each step. 

There are two options for deployment: [Major-Version Deployment](#major-version-deployment) and [Minor or Patch Deployment](#minor-or-patch-deployment). The difference is that the major-version release includes updates to the database structure and therefore requires additional steps.

### Major-Version Deployment
> The single database for each environment referenced here is assumed to refer to the primary database, but these steps should be used for each database undergoing structural updates.

Major-version releases will likely involve updates to the database structure or data and may involve ETL, which increase the complexity and risk of a release to the production environment. If there are changes to the database structure, continue with the steps in this section. Otherwise, skip to the [Minor or Patch Deployment](#minor-or-patch-deployment) section.

1. Back up the PROD database (solely to restore into STAGE - another backup with be taken just before going live).
    
    Use the `pg_dump` command in [Transferring Between Databases](#transferring-between-databases).

2. Drop and recreate the `public` schema in the STAGE database. This ensures a clean slate for the data transfer.

    **WARNING: MAKE SURE THE CORRENT (STAGE) DATABASE IS USED OR UNEXPECTED DATA LOSS WILL OCCUR**

        psql --host=<hostname> --port=5432 --username=<username> --dbname=<STAGE_database_name> --command="DROP SCHEMA public CASCADE;" --command="CREATE SCHEMA public;"
        <Enter password>

    Troubleshooting - if this command hangs, try disabling long-running idle queries:

        SELECT pg_terminate_backend(pid) from pg_stat_activity
        WHERE state in ('<IDLE> in transaction', 'idle in transaction')
        AND now()-xact_start>interval '1 minute';

3. Restore the structure and data of the STAGE database from PROD.

    Use the `pg_restore` command in [Transferring Between Databases](#transferring-between-databases), with the STAGE database name as \<target_database_name\>.

4. Continue with Steps 5-7 using STAGE as the 'target' environment.

5. Migrate Django changes to the target database. This uses the 'developer_\<env\>_user' specified in the [database setup summary](#database-setup-summary).

6. Run any ETL script(s) against the target database. The ETL should include its own automated verification.

7. Manually verify data integrity at the database level.

1. Deploy the app, using `getyour.settings.stage` settings in `manage.py`. All deployments use the STAGE site, but this specifies the STAGE database for pre-PROD testing.

    See [Deploy Django for Production](#deploy-django-for-production) for steps.

1. Manually verify STAGE site and database functionality. Depending on the complexity of changes, this may include:

    - Going through the application from the beginning to ensure functionality and that the data update properly (recommended)
    - Logging in as an existing user to ensure functionality (recommended)
    - Manually triggering a renewal and go through the process to ensure functionality and data integrity

    Refer to `/ref/uat_plan.md` for detailed verification steps.

1. Select a time when users aren't using the PROD site; stop the site service.

1. Back up the PROD database in preparation for deployment to PROD.

    Use the `pg_dump` command in [Transferring Between Databases](#transferring-between-databases).

1. Follow Steps 5-7 using PROD as the 'target' environment.

1. Deploy the app, using `getyour.settings.production` settings in `manage.py`. All PROD deployments use the STAGE site, but this specifies the PROD database so that the sites are swappable without further changes.

    See [Deploy Django for Production](#deploy-django-for-production) for steps.

1. Swap the STAGE and PROD deployment slots.
    > This must be done while the site service is down because the prior-version PROD site is expecting a different database structure or data.

    This is done with the 'Swap' option in the Deployment > Deployment Slots screen in the Azure Portal.

1. Start the PROD site service.

1. Manually verify functionality using the PROD site. Depending on the complexity of changes, this may include:

    - Going through the application from the beginning to ensure functionality and that the data update properly (recommended)
    - Logging in as an existing user to ensure functionality (recommended)
    - Manually triggering a renewal and go through the process to ensure functionality and data integrity

    Refer to `/ref/uat_plan.md` for detailed verification steps.

    > This can be abbreviated since extended testing was completed earlier

### Minor or Patch Deployment
**These steps are for releases that do not include database structure or data updates.** If database structure or data updates are included, the release is not backward-compatible; it should be a major release and **must** use the steps in [Major-Version Deployment](#major-version-deployment) instead.

1. Back up the PROD database.

    Use the `pg_dump` command in [Transferring Between Databases](#transferring-between-databases).

1. Deploy the app, using `getyour.settings.production` settings in `manage.py`. All PROD deployments use the STAGE site, but this specifies the PROD database so that the sites are swappable without further changes.

    See [Deploy Django for Production](#deploy-django-for-production) for steps.

1. Manually verify functionality using the STAGE site. Depending on the complexity of changes, this may include:

    - Going through the application from the beginning to ensure functionality and that the data update properly (recommended)
    - Logging in as an existing user to ensure functionality (recommended)
    - Manually triggering a renewal and go through the process to ensure functionality and data integrity

    Refer to `/ref/uat_plan.md` for detailed verification steps.

1. Swap the STAGE and PROD deployment slots.

    This is done with the 'Swap' option in the Deployment > Deployment Slots screen in the Azure Portal.

1. Manually verify functionality using the PROD site. Depending on the complexity of changes, this may include:

    - Going through the application from the beginning to ensure functionality and that the data update properly (recommended)
    - Logging in as an existing user to ensure functionality (recommended)
    - Manually triggering a renewal and go through the process to ensure functionality and data integrity

    Refer to `/ref/uat_plan.md` for detailed verification steps.

    > This can be abbreviated since extended testing was completed earlier

### Deploy Django for Production
These steps deploy the Django site for production. Note that the STAGE site is always used here; as noted earlier in this section, PROD is always hot-swapped from the STAGE deployment slot.

1. In the `Get-Your/Get-Your` local Git repo, pull the latest changes to the `main` branch. These changes should include the release/tag for the specified release.

1. In the `Get-Your/Get-Your-utils` repo, execute `/get_your_utils/powershell/docker_deploy/BuildDeployDocker.ps1`. This will prompt the user for the target environment, build the `Get-Your` Docker container, and deploy it to the environment-specific tag in Docker Hub.

    The `.env.template` file must be copied to `.env` and the variables filled. The build/deploy script assumes that each repo shares a parent directory on the local device, such as a `git` parent directory like `git/Get-Your` and `git/Get-Your-utils`.

1. Once the script has completed without errors, the STAGE site will automatically update with the latest code.

# App Secrets
App secrets are loaded into the Docker container as environment variables via the `.*.deploy` files (`.dev.deploy` and `.prod.deploy`, for each [database server instance](#database-setup-summary)) and `secrets.*.toml` files (`secrets.dev.toml` and `secrets.prod.toml`, for each [database server instance](#database-setup-summary)). Each of the four files has a `*.template` template to fill with the relevant variables, found in the `/ref/env_vars` directory.

The difference between `secrets.*.toml` and `.*.deploy` file usage can be found in [Development and Deployment](#development-and-deployment).

# Azure App Service Frontend

## App Service Plan
The 'Standard S1' pricing plan was selected for the App Service Plan. This has the following benefits over the cheaper 'Basic B1' pricing plan:

- Auto-scale up to 10 instances (instead of manual up to 3) (subject to availability)
- Up to 5 staging slots for testing before swapping into prod (this is the primary reason for selecting this pricing plan - see [Web App](#web-app))
- Daily backups (10x daily)
- Traffic manager for instances of app
- 50 GB disk storage shared between apps (vs 10 GB for B1)

## Web App
The Azure service for the Get FoCo app is a Linux-based Docker container Web App. The PROD app was created as a new Web App, then DEV and STAGE apps created as 'deployment slots' of the PROD app. This allows hot-swapping either of the other apps into PROD (although in practice, only the STAGE slot is swapped with PROD).

# Azure File Store Backend

## File Store Setup Description
See [Azure file store selection docs](https://docs.microsoft.com/en-us/azure/storage/files/storage-how-to-create-file-share?tabs=azure-portal) for reference.

Blob Storage is used for storage of user files from Django. The app uses `azure-blob-storage` for the connection; see `/ref/env_vars/.dev.deploy.template` and `/ref/env_vars/secrets.dev.toml.template` for the necessary variables to make the connection.

# Azure Database Backend

## Database Setup Summary
Summary of the database setup

- Azure Database for PostgreSQL Flexible Server
  - Burstable compute tier
- Separate instances for DEV and PROD/STAGE
  - Each instance has users named for that instance to avoid confusion
  - Each instance has database(s) named for the environment to avoid confusion
- Database names
  - `platform_dev` is the database name on the DEV server instance
  - `platform_stage` and `platform_prod` are separate databases on the PROD server instance
  - The 'analytics' counterpart (used by Django for logging) is its own database in each environment (specified where necessary as \<analytics_database\>)
- Database users (\<env\> is the database instance for each user ('dev', 'stage', or 'prod'))
  - developer_\<env\>_user: Privileged database user, used locally for Django development
  - django_\<env\>_user: Base database user, used by Django with the minimum necessary database privileges

## Database Setup Description
Each database is set up in an Azure Database for PostgreSQL instance. Flexible Server was chosen for the instance type, due to the Burstable compute tier (Single Server was the initial choice, but the Burstable tier is more performant and costs approximately the same as Single Server (for the low loads expected on this site)). See [Microsoft's comparison chart](https://docs.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-compare-single-server-flexible-server) for more details.

In order to properly separate the DEV and STAGE/PROD databases as well as use less-expensive performance settings on the DEV database, two separate Azure Database for PostgreSQL server instances were used. DEV has its own instance and uses a database named `platform_dev`. The PROD server instance houses both `platform_stage` and `platform_prod` databases, for STAGE and PROD, respectively.

## Database Administration
This section relies on the adminstrator to have locally installed the same version of Postgres being used in the Azure instance (the utility versions must match).

For the following sections,

`<source...` prepends the source objects (where applicable), and

`<target...` prepends the target objects

### Connectivity
Database administration can be completed in any application, but `psql` is the basic GUI incorporated with Postgres that provides simple access to the database.

Use the following connection string to connect to the target database. The hostname and admin username can be found under the 'Essentials' section at the top of the Overview page on the Azure Portal as 'Server name' and 'Server admin login name', respectively.

    psql --host=<hostname> --port=5432 --username=<username> --dbname=<database_name>
    <Enter password>

`pg_dump` and `pg_restore` are PostgreSQL utilities used from the local command line (e.g. not from within the `psql` connection).

### Creating a Database
On a freshly-deployed Azure instance, only the admin user (assigned during server setup) and the `postgres` database exist. Use the following code to create the `platform` database and its 'analytics' counterpart.

    psql --host=<hostname> --port=5432 --username=<admin_username> --dbname=postgres --command="CREATE DATABASE <target_database_name>;"

### Transferring Between Databases
During the setup phase, there was much experimentation of Azure instance types; Azure tenant selection; and database naming conventions before settling on the final version, so transferring structure and data was necessary. The following code can be used to transfer existing data to the new database.

If there isn't yet existing data, just run Django migrations to the new \<target_database_name\>.

> If the same users aren't present in the target database as there are in the source, the `pg_restore` command will throw errors. To ignore object owners specified in the backup file and instead use the input username as the owner of all objects, add the flag `--no-owner` to the `pg_restore` command. This is not recommended because the permissions structure for Get-Your is strictly defined.

    # Dump the database structure and data in a custom format to a local file for pg_restore
    # <target_local_backup_file> can have any extension
    pg_dump -Fc -v --host=<source_hostname> --username=<source_admin_username> --dbname=<source_database_name> -f <target_local_backup_file>

    # Restore the structure and data to the target database
    pg_restore -v --host=<target_hostname> --port=5432 --username=<target_admin_username> --dbname=<target_database_name> <target_local_backup_file>

### Set Up Database Users
This section details the order of steps to set up users, roles, and proper permissions. Roles are used for generic permissions so that future users can be added without having to re-grant all permissions.

The admin user shouldn't be used for development or live database connections; a privileged user should instead be created for local development access and a base user created with minimal privileges for the webapp. The privileged user will be stored in each environment's `secrets.*.toml` file and the base user will be in the `.*.deploy` file (see [App Secrets](#app-secrets)).

#### Configure the Primary Database
This section should be used for the `platform` database, for the initial configuration. It includes definitions that only need to be run once.

Connect to the primary (`platform`) database and complete the following steps:

1. Revoke initial access

    Azure Database for Postgres Flexible Server with Postgres-only Authentication gives full access to the 'public' role by default (which is counterintuitive). Run these commands once on a new database to reset to zero-trust (where \<database_name\> is the database for use with Django, e.g. `platform_dev`).

        REVOKE ALL ON SCHEMA public FROM public;
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM public;
        REVOKE ALL ON DATABASE <database_name> FROM public;
        REVOKE ALL ON DATABASE azure_maintenance FROM public;
        REVOKE ALL ON DATABASE azure_sys FROM public;
        REVOKE ALL ON DATABASE postgres FROM public;

1. Create admin role

    Create and grant permissions to an admin user role (named `admin_role`) without login privileges, then grant this role to the Postgres admin account.

        CREATE ROLE admin_role INHERIT;
        GRANT ALL ON SCHEMA public TO admin_role;
        GRANT ALL ON DATABASE <database_name> TO admin_role;
        GRANT ALL ON ALL TABLES IN SCHEMA public TO admin_role;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO admin_role;
        GRANT ALL ON DATABASE postgres TO admin_role;        
        GRANT admin_role TO <admin_user>;

1. Create basic role

    Create and grant permissions to a base user role (named `base_role`, for use via Django) without login privileges.

        CREATE ROLE base_role INHERIT;
        GRANT CONNECT ON DATABASE <database_name> TO base_role;
        GRANT USAGE ON SCHEMA public TO base_role;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO base_role;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO base_role;

1. Create privileged role

    Create and permissions privileged user role (named `privileged_role`, for local developer use) without login privileges. Start by granting `base_role` permissions then add CREATE/DROP table permissions.

        CREATE ROLE privileged_role INHERIT;
        GRANT base_role TO privileged_role;
        GRANT CREATE ON SCHEMA public TO privileged_role;

1. Create and assign users

    Create users (with passwords and login privileges) and assign the proper role to each (`base_role` for Django users, `privileged_role` for local developers).

        CREATE USER <username> WITH LOGIN PASSWORD '<password>' INHERIT;
        GRANT <role> TO <username>;

1. Alter default privileges

    Once the privileged user *(not role)* is created, GRANT that user to the admin user so that the admin user can alter default privileges on behalf of the privileged user. Altering the default privileges as below will ensure `base_role` (and users within that role) has the proper privileges on any new tables and sequences within any schema created by the privileged user.

    > Note that the ALTER DEFAULT PRIVILEGES command is run *for* the table-creation user (privileged user) *to* `base_role`, meaning that the default privileges are being changed for `base_role` on anything created by the privileged user. Because it's specific to the privileged user and not the privileged *role*, the ALTER DEFAULT PRIVILEGES command will need to be repeated for each privileged user that will be creating objects (e.g. tables, schemas, etc).

        -- Grant this role to admin user to alter default privileges
        GRANT <privileged_user> TO <admin_user>;
        
        -- This is so all privileges for `base_role` apply to any new objects created by <admin_user>
        ALTER DEFAULT PRIVILEGES FOR ROLE <admin_user> GRANT USAGE ON SCHEMAS TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <admin_user> GRANT CREATE ON SCHEMAS TO privileged_role;

        -- This is so all privileges for `base_role` apply to any new objects created by <privileged_user>
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT ALL ON SEQUENCES TO base_role;

#### Configure Other Databases
This section should be used for all other databases on the same server (such as the 'analytics' database used for logging). It relies on the roles that were created in the [previous section](#configure-the-primary-database).

Connect to the database to configure and complete the following steps:

1. Revoke initial access

        REVOKE ALL ON SCHEMA public FROM public;
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM public;
        REVOKE ALL ON DATABASE <database_name> FROM public;
        REVOKE ALL ON DATABASE postgres FROM public;

1. Grant permissions to the (existing) admin user role

        GRANT ALL ON SCHEMA public TO admin_role;
        GRANT ALL ON DATABASE <database_name> TO admin_role;
        GRANT ALL ON ALL TABLES IN SCHEMA public TO admin_role;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO admin_role;
        GRANT ALL ON DATABASE postgres TO admin_role;        

1. Grant permissions to the (existing) base user role

        GRANT CONNECT ON DATABASE <database_name> TO base_role;
        GRANT USAGE ON SCHEMA public TO base_role;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO base_role;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO base_role;

1. Grant permissions to the (existing) privileged user role

        GRANT CREATE ON SCHEMA public TO privileged_role;

1. Alter default privileges
        
        -- This is so all privileges for `base_role` apply to any new objects created by <admin_user>
        ALTER DEFAULT PRIVILEGES FOR ROLE <admin_user> GRANT USAGE ON SCHEMAS TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <admin_user> GRANT CREATE ON SCHEMAS TO privileged_role;

        -- This is so all privileges for `base_role` apply to any new objects created by <privileged_user>
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT ALL ON SEQUENCES TO base_role;

# Email Settings
SendGrid is the service used in this app to send automated email to users. Anything in this section references the `sendgrid` package, although a planned change will be to use [`django-anymail`](https://anymail.dev/en/stable) with the SendGrid option instead in order to genericize the email code.

For the best user experience, the recommended email address to accept correspondence is the same address that automated emails are sent from. The code is set up this way, such that the `contact_email` variable is propagated throughout.

# Phone Settings
Twilio is the service used in this app to [send SMS](#sending-sms) and [receive voice calls](#call-forwarding).

For the best user experience, the recommended number to accept calls is the same number that automated SMS are sent from. The code is set up this way, such that the `TWILIO_NUMBER` configuration variable is propagated throughout (prettified for display as `contact_number`). The [call-forwarding](#call-forwarding) section goes through the steps of setting up the SMS-sender number to forward voice calls to a real phone number.

## Sending SMS
Something here about how to set up Twilio to send SMS...

## Call-Forwarding
Voice calls from users are set up for simple pass-through forwarding. This is configured from the Twilio console.

### Call-Forwarding Setup
Twilio provides a simple page for initial setup, found at https://www.twilio.com/code-exchange/simple-call-forwarding under the default 'Quick Deploy to Twilio' tab. If the admin is already logged in to Twilio, all fields except 'My Phone Number' under Step 2 are prefilled. Fill in the number to forward to and select 'Deploy this application'.

![Twilio Quick Deploy a forwarding number][1]

To change the forwarding number, see [Call-Forwarding Configuration](#call-forwarding-configuration).

## Call-Forwarding Configuration
To reconfigure the voice forwarding function or change the target phone number, navigate to the function in the Twilio console.

1. From the initial screen once logged in to Twilio, select 'Explore Products +'.

1. Under the Developer Tools section, find 'Functions and Assets'. Select the pushpin icon to pin in to the Twilio sidebar navigation.

    > The sidenav will likely not look like the screenshot; all that matters here is the 'Functions and Assets' section.

    ![Pin 'Functions and Assets' to Twilio sidebar][2]

1. Once it's on the sidenav, expand Functions and Assets and select Services.

1. Select the name of call-forwarding service, shown here with the Twilio default "forward-call".

    ![Call-forwarding service via Twilio Functions][3]

1. The screen that opens allows editing of key files, including the `/forward-call` JS function that runs the service. For updating a phone number (e.g.changing the forward-to phone number or the affected Twilio number), however, select the 'Environment Variables' option.

    ![Environment Variables option for the forward-call function][4]

1. The `TWILIO_PHONE_NUMBER` and `MY_PHONE_NUMBER` values are the numbers that users can call and the forward-to number, respectively.

    ![Environment variables used by the forward-call function][5]

    To edit a value, select the 'Edit' option. Ensure that the new number is input with the same format as the currently-displayed value (e.g. "+\<country_code\>..."). When finished, select the 'Update' button; the log directly below the environment variables should show 'updating' then 'saved', at which point the new number is in effect.
    
    > The 'Deploy All' button at the bottom of the window is unnecessary for just changing environment variables.

    ![Updating an environment variable in the forward-call function][6]


# Request a Consultation

The Get FoCo team is proud of the product we've created and we've released it as open-source to encourage its use in other organizations. If you'd like a consultation for implementing in your organization, please contact any of the program contributors with what you're looking for and we'll be in touch:

Tim Campbell (program integration, backend development): `ConsultTim [at] outlook [dot] com`

Andrew Hernandez (software development): `JonAndrew [at] outlook [dot] com`

Jade Cowan (software development): `jade.cowan [at] penoptech [dot] com`

# Appendix

## Database Administration Tools

### Delete User
This is in the event a user needs to be deleted (except the original admin user, which can't be deleted). A role can be deleted using this same method, but permissions will need to be dispersed to a new user if proper access is to be maintained.

    REVOKE privileged_role FROM <username> CASCADE;
    REVOKE base_role FROM <username> CASCADE;
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM <username> CASCADE;
    REVOKE ALL ON SCHEMA public FROM <username> CASCADE;
    REVOKE ALL ON DATABASE <database_name> FROM <username> CASCADE;

    -- Run one of these lines if DROP USER returns an error

    -- This will reassign any objects owned by the user to be deleted
    --REASSIGN OWNED BY <username> TO <new_owner_username>;

    -- OR, this will drop any objects owned by the user to be deleted
    --DROP OWNED BY <username>;
    
    DROP USER <username>;



[1]: ./media/twilio_quick_deploy_forwarding.png
[2]: ./media/twilio_pin_functions_and_assets.png
[3]: ./media/twilio_functions_services.png
[4]: ./media/twilio_forward_call_initial_screen.png
[5]: ./media/twilio_forward_call_env_vars.png
[6]: ./media/twilio_forward_call_update_phone_number.png