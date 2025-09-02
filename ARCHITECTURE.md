# Architecture

Here you will find high-level architecture of Get FoCo.
Getting to know Get FoCo starts here!

## Top Level![Get FoCo Process Flow](https://user-images.githubusercontent.com/72939569/198737977-8c08368e-d138-4493-a637-df12e332ef4a.png)


Get FoCO is a web-app that allows residents of Fort Collins to create accounts with their financial information and income verification (SNAP, EBT, PSD Letter, ACP Letter) which then is used by Get FoCo to see what kind of income qualified programs they may qualify for.

It is a 6 step process

Step 1
Client creates their account with email, phone number, etc.

Step 2
Client uploads their address information to see if they qualify for location based IQ Programs

Step 3
Client inputs their financial information such as gross annual AMI and number of people in household - the system uses this information to double check programs they may qualify for

Step 4
Client inputs which income verification programs they may be a part of (if any) - this is used to validate clients' income which, again, is used to double check which programs they may qualify for.

Step 5
Client uploads their income verification proof, i.e. a picture or pdf of a SNAP card, etc.

Step 6
Final step! Client is then emailed to verify account creation and finally...

Dashboard
Using the information from steps 1 - 6, the dashboard uses logic and facts to figure out which IQ programs a client may qualify for - at the dashboard these programs are shown and clients are able to click on "quick-apply" to apply for programs.

## Code Map
Here you will find brief explanations of files, directories and data structures.

## Architecture
The web app is split up into two sections called "application" and "dashboard" - you can better see how these two sections are divided by visiting the "mobileVers/application" and "mobileVers/dashboard" directories. 



## Admin

Here is the main settings directory for Get FoCo, this section holds key information and settings utilities. These include Dockerfile, workflows, etc.

### '.github/workflows'
Future workflow GitHub implementation.

### '.vscode/settings.json'
settings.json file for vscode. May no longer be needed.

### 'mobileVers/'
Files not in folders are all crucial Docker files or django necessary files such as requirements to get Get FoCo up and running locally.

### 'mobileVers/Dockerfile'
Crucial Docker file holding instructions to containerize Get FoCo using Docker, subsequent files, entrypoint.sh and init.sh are utilized in tandem to create a pleasant Docker containerizing experience.

## Application
Application holds steps 1 - 4 of the application as well as the index page, privacy policy, file upload page for parts of the application and future parts of the application that require more files (I.E. recreation portion of Get FoCo that requires extra steps) and pages that aren't directly tied to dashboard pages. 


### 'mobileVers/application/backend.py'
Here you'll find some useful backend logic / functions used in the main application, most of these functions are used to 
supplement the application and to keep views.py clutter to a minimum! Functions include USPS, address and Twilio.

### 'mobileVers/application/forms.py'
Here you'll find important forms information for the "application" part of the webpage. These forms hold steps 1-4 of the application.

### 'mobileVers/application/models.py'
Here you'll find models used for the database in tandem with the forms to create critical tables for the database. This models file pertains to the 'application' portion of Get FoCo.

### 'mobileVers/application/views.py'
This file contains the crucial "application" (I.E. steps 1 - 4 of Get Foco) logic. This file contains some important AMI logic, as well as the views for steps 1-4, index page, and separate quick apply views pages for the dashboard.

### 'mobileVers/application/'
Directory for critical files for the "/application/" part of Get FoCo

### 'mobileVers/application/static/application'
Holds static images used to make Get FoCo look good, images include icons found throughout Get FoCo.

### 'mobileVers/application/static/scripts/main.js'
Holds ajax script for important functions found in various steps of the application. Examples include ajax implementation of checks to make sure page checks that all fields are filled out and are completely correct. 

### 'mobileVers/application/static/application/'
Holds HTML templates for Get FoCo, of everything that is within the /application/ part of the site. 

### 'mobileVers/application/test/'
Here are where unit tests are found, tests still need to be implemented!

## Dashboard
Dashboard contains steps 5 and 6 as well as the Dashboard of GetFoCo and all of the pages that go within (i.e. settings page for clients, Get FoCo Bag Badge, etc.)

Some thing to note is a future update to Get FoCo should separate steps 5 and 6 from Dashboard and place it in Application! For some reason during the initial stages of Get FoCo, we split up steps 5 and 6 into dashboard. 

### 'mobileVers/dashboard/'
Directory for critical files for "/dashboard/" part of Get FoCo

### 'mobileVers/dashboard/backend.py'
Here you'll find some useful backend logic / functions used in the dashboard, most of these functions are used to 
supplement the application / dashboard and to keep views.py clutter to a minimum! Functions include page logic for breadcrumbs, authenticating users and blob storage integration

### 'mobileVers/dashboard/forms.py'
Here you'll find important forms information for the "dashboard" part of the webpage. These forms hold steps 5 - 6 of the application.

### 'mobileVers/dashboard/models.py'
Here you'll find models used for the database in tandem with the forms to create critical tables for the database. This models file pertains to the 'dashboard' portion of Get FoCo, that is to say files, file uploads, tax information and feedback.

### 'mobileVers/dashboard/views.py'
This file contains the crucial "/dashboard/" (I.E. steps 5 - 6 + dashboard + auxiliary pages of more income verification in quick apply applications of Get Foco) logic. This file contains some important AMI logic, as well as the views for steps 1-4, index page, and separate quick apply views pages for the dashboard. Dashboard logic very very important in this file, marked at qualifiedPrograms and def dashboardGetFoco

### 'mobileVers/dashboard/static/dashboard/'
Holds static images used to make Get FoCo look good, images include icons found throughout Get FoCo.

### 'mobileVers/dashboard/static/templates/'
Holds HTML templates for Get FoCo, of everything that is within the /application/ part of the site. 

### 'mobileVers/dashboard/test/'
Here are where unit tests are found for "/dashboard/" section of website, tests still need to be implemented!

### 'mobileVers/mobileVers/media/'
Files for local instances found here!

### 'mobileVers/mobileVers/settings/'
Dev, local and production settings are found here, each one corresponds to a different environment, for example, dev uses the dev postgresql database.

### 'mobileVers/mobileVers/static/'
Files that are generated when python collecstatic is run

