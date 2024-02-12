# Get FoCo

The universal income-qualified application for the City of Fort Collins, Colorado.

// TODO: write README

# Table of Contents
1. [Get FoCo](#get-foco)
1. [Running the App](#running-the-app)
1. [Development and Deployment](#development-and-deployment)
    1. [manage.py](#managepy)
    1. [Local Development](#local-development)
    1. [Hybrid Development](#hybrid-development)
    1. [Deployment](#deployment)
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

    python3 manage_local.py migrate
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

## Deployment
Deployment consists of building and pushing the Docker container, then pulling into the Azure [Web App](#web-app). Get FoCo is set up for the following:

- DEV
  - The container is manually built and pushed to Docker Hub
  - The DEV Web App has a webhook to pull the `dev` tag whenever it's updated
- STAGE
  - TODO: When the `main` branch is manually pulled into a repo in the private City of Fort Collins Github organization, a Github Action builds and pushes the container to Docker Hub using the latest Git tag and also the `prod` container tag
  - The STAGE Web App has a webhook to pull the `prod` tag whenever it's updated
- PROD
  - PROD is manually swapped from STAGE only after STAGE has been verified

Deployment uses `.dev.deploy` and `.prod.deploy` for DEV and STAGE/PROD [app secrets](#app-secrets) (respectively).

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
  - The 'analytics' counterpart (used by Django for logging) is its own database in each environment
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

    `psql "host=<hostname> port=5432 dbname=<database_name> user=<username> sslmode=require"`
    <Enter password>

`pg_dump` and `pg_restore` are PostgreSQL utilities used from the local command line (e.g. not from within the `psql` connection).

### Creating a Database
On a freshly-deployed Azure instance, only the admin user (assigned during server setup) and the `postgres` database exist. Use the following code to create the `platform` database and its 'analytics' counterpart.

    psql "host=<hostname> port=5432 dbname=postgres user=<admin_username> sslmode=require"

    -- These lines are within the database
    CREATE DATABASE <target_database_name>; -- Create the target database
    \q -- Quit out of the database connection

### Transferring Between Databases
During the setup phase, there was much experimentation of Azure instance types; Azure tenant selection; and database naming conventions before settling on the final version, so transferring structure and data was necessary. The following code can be used to transfer existing data to the new database.

If there isn't yet existing data, just run Django migrations to the new \<target_database_name\>.

    # Dumps the database structure and data in a custom format to a local file for pg_restore
    # <target_local_backup_file> can have any extension
    pg_dump -Fc -v --host=<source_hostname> --username=<source_admin_username> --dbname=<source_database_name> -f <target_local_backup_file>

    # Restore the structure and data *with no owner* to the target database
    # --no-owner is necessary for proper setup
    pg_restore -v --no-owner --host=<target_hostname> --port=5432 --username=<target_admin_username> --dbname=<target_database_name> <target_local_backup_file>

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

        -- This is so all tables GRANTs apply to new tables as well
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT USAGE ON SCHEMAS TO base_role;
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

        -- This is so all tables GRANTs apply to new tables as well
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT USAGE ON SCHEMAS TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO base_role;
        ALTER DEFAULT PRIVILEGES FOR ROLE <privileged_user> GRANT ALL ON SEQUENCES TO base_role;

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