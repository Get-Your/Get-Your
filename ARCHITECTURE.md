# Get-Your

Get-Your is an online application for income-qualified programs supported by any organization.

This was created for the City of Fort Collins, so references will be to their version of the app, 'Get FoCo'.

# Table of Contents
1. [Get-Your](#get-your)
1. [Background](#background)
1. [Definitions](#definitions)
    1. [Account](#account)
    1. [AMI](#ami)
    1. [Benefits](#benefits)
    1. [City Limits](#city-limits)
    1. [Eligibility Address](#eligibility-address)
    1. [Eligibility Programs](#eligibility-programs)
    1. [GMA](#gma)
    1. [Household](#household)
    1. [IQ Programs](#iq-programs)
    1. [Mailing Address](#mailing-address)
    1. [Platform (codebase)](#platform-codebase)
    1. [Platform Administrator](#platform-administrator)
    1. [Program Coordinator](#program-coordinator)
    1. [Project (codebase)](#project-codebase)
    1. [User](#user)
    1. [Verification Staff](#verification-staff)
1. [Process Flows](#process-flows)
    1. [User Process](#user-process)
    1. [Verification Staff Process](#verification-staff-process)
        1. [User list view](#user-list-view)
        1. [User view](#user-view)
    1. [Program Coordinator Process](#program-coordinator-process)
1. [Project Code Map](#project-code-map)
    1. [Configuration Files](#configuration-files)
    1. [`app`](#app)
    1. [`dashboard`](#dashboard)
    1. [`files`](#files)
    1. [`monitor`](#monitor)
    1. [`ref`](#ref)
    1. [`users`](#users)

# Background

The City of Fort Collins provides many income-qualified programs to residents. Prior to Get-Your (and Get FoCo), however, these programs would typically require applicants to

1. Travel in-person to the department that runs a program
1. Fill out a physical form and provide income-verification documentation (usually tax forms)
1. Wait to hear if they've been enrolled (and each program had different methods of response)
    1. This could take quite a while due to the overextended staff at each department

Furthermore, almost every program is run from a different department! These steps posed a large barrier for members of the low-income community, especially because of the amount of time it takes to travel to an office. There was also the problem that Fort Collins didn't have many applicants with overlapping programs, even though most programs have the same level of qualification requirements. This was attributed to the difficulty in learning about the available programs.

Get-Your was designed to solve these problems.

- The first key feature is that users fill out a *single* application which is applicable to all income-qualified programs on the platform. Filling out information only once is a huge reduction in effort for potential applicants
- With it being online-only, there is no travel time. Studies have shown that smartphone usage as a sole Internet-enabled device is high among the intended audience of Get-Your, so it has a mobile-first design
    - For those without Internet access, the application can be filled out at public libraries
    - Critically, for those uncomfortable with web interfaces, the City of Fort Collins has set up in-person help at popular community locations (e.g. the Fort Collins Senior Center)
- Applicants will need to upload ID and paperwork, which can be done with a smartphone camera
    - Additionally, these documents are now stored securely (and soon to be governed by a data retention policy). Since tax forms are no longer allowed, critical PII is not stored at all
- Because there is a single application per user, dedicated staff can be tasked with verifying documents. Once a user has been verified, each program's department only needs to perform their process of enrolling users (no longer verifying themselves)
    - Wait times are lower, and the online nature of the platform can give feedback to the user

# Definitions

## Account
Accounts within Get-Your are created by a [user](#user) on behalf of a [household](#household).

## AMI
AMI stands for Area Median Income, which is the median income of all households in the area that the organization administering Get-Your is located.

For Get FoCo, the City of Fort Collins uses their [Growth Management Area](#gma) as the 'area' the AMI is referring to.

## Benefits
Benefits are defined by each [IQ Program](#iq-programs) and dispersed / made available to all enrolled [accounts](#account).

Benefits within Get-Your apply to the [household](#household) (not an individual person), so while the [user/applicant](#user) who created the [account](#account) may be referenced specifically within this document, all verifications and benefits apply to the entire household.

## City Limits
In the US, the boundaries within which a city is responsible.

## Eligibility Address
The address used to determine geographical eligibility for a household.

This is gathered with the page header 'Where do you live?' as a simple question that doesn't require explaining the behind-the-scenes process to the user.

## Eligibility Programs
External programs that the organization uses to determine income eligibility.

Rather than accept tax documentation or low-level financials, the platform piggybacks off outside organizations for verification purposes (e.g. SNAP and Medicaid); each Eligibility Program is correlated from its source designation to local [AMI](#ami) (Area Median Income). For example, SNAP is defined as 130% of Federal Poverty Level; that translates to 30% AMI in Fort Collins, so that would be the 'AMI threshold' for a SNAP-card upload in Get FoCo.

## GMA
In the US, the Growth Management Area of a city designates the furthest limits that a city can expand. The encompassing county is responsible for services wherever the GMA boundary doesn't match the [city limits](#city-limits).

## Household
A household means the [applicant](#user) and any other people claimed on their federal tax return, included in Get-Your under one [account](#account) (so that [benefits](#benefits) can be provided properly).

This was defined by the City of Fort Collins and Code for America teams that originally set up Get-Your.

## IQ Programs
These are the Income-Qualified Programs offered by the organization via the Get-Your app.

## Mailing Address
The address where mail from Get-Your can be sent.

This can be different than [Eligibility Address](#eligibility-address) to allow for cases where the applicant must temporarily live away from their official residence (such as domestic abuse).

## Platform (codebase)
When referring to the codebase, the "platform" is everything in the repo. This generally references files in the repo root, such as `uv` definitions, .MD documentation, and Git definitions; everything else will likely be referred to by the [project](#project-codebase) moniker, as they are specific to the Django portion of the platform.

The platform is governed by [`uv`](https://docs.astral.sh/uv), which installs the necessary dependencies for the [Django project](#project-codebase) and everything included within.

## Platform Administrator
The Platform Administrator(s) administers the Get-Your platform for their organization. On the platform, they are responsible for defining the Eligibility Programs and IQ Programs.

## Program Coordinator
Get-Your doesn't connect to external systems because it generally assumes [IQ Programs](#iq-programs) are administered by separate departments, so the Program Coordinator(s) are responsible for extracting (verified*) applicants from Get-Your and enrolling them in their specific program in whatever system they use. Once completed, the Program Coordinator(s) will mark each applicant 'enrolled' in Get FoCo so that it's displayed on the user's dashboard.

\* All applicants that can be viewed by the Program Coordinator have already been verified by the [Verification Staff](#verification-staff); see [Verification Staff Process](#verification-staff-process) for additional details.

## Project (codebase)
When referring to the codebase, the Django portion of this repo -- all code within the 'get_your' directory -- is referred to as a "project" (or "Django project"). This is in contrast to the [platform](#platform-codebase), which is governed at the repo root.

## User
A 'user' of the platform is an end-user who has created an [account](#account) on behalf of their [household](#household). This is generally synonymous with 'applicant' in this document.

## Verification Staff
This is the staff member(s) responsible for verification of identification and Eligibility Program uploads. This user(s) will mark each applicant 'verified' once uploads have been confirmed as complete and accurate.

# Process Flows

## User Process
> ![NOTE]
> The [Get FoCo Process Flow](https://user-images.githubusercontent.com/72939569/198737977-8c08368e-d138-4493-a637-df12e332ef4a.png) Fort-Collins-specific details about this process.

Get-Your allows users to create accounts, upload identification and income verification documentation, then apply for income-qualified programs. A new user's process is described below, starting with selecting 'Apply' from the main landing page:

0. Preliminary step: the user is displayed a 'before we get started' page with descriptions of the [accepted external programs] ([Eligibility Programs](#eligibility-programs)) as well as the organization's [privacy policy]. This page is informational.

    This is defined with `app.views.get_ready()`.

1. Account creation: the user enters their name, email, and phone number, and a password to create an account.

2. Address: the user enters the address at which their household resides (their [Eligibility Address](#eligibility-address)), as well as a separate mailing address, if applicable.

    The system will attempt to confirm each address with USPS. See [Address] for additional details on the usage of these addresses and confirmation steps.

3. Household information: the user enters minimal demographic information, then the number of individuals in their household. The 'number of individuals' is used solely to populate the next page; this is planned to be removed as a form field (instead inferred from the information entered) so that both parts of this step are on a single page.

    On the next page, the user enters the full name and birthdate and uploads a form of identification for each individual in the household. See [Supported Identification] for additional details on this upload.

4. Eligibility Program selection: from a list of external programs (the [same as in the preliminary step]), the user chooses all they are enrolled in.

5. Eligibility Program uploads: the user is prompted to upload supporting documentation for each program selected in the prior step.

6. New account confirmation: a page is displayed that confirms the account, and says that the user will be sent an email and text to confirm as well. See [User Communication] for additional details on the notifications.

7. Dashboard: The user can then continue to the dashboard, where all income-qualified programs ([IQ Programs](#iq-programs)) the user is eligible for are displayed in the 'Available Programs' section (those that the user doesn't qualify for are not included at all), along with a News section and a simple user-feedback mechanism.

    The user can select 'Apply Now' next to any displayed program, at which point the system will display a confirmation page and that program will be moved to the 'Pending Approval' section. Once the user is enrolled for a program, it will be displayed in the 'Active Programs' section.

This was designed to be synchronous for the user; all steps can be completed in one sitting, without needing input from the organization. The organization will, of course, need to verify that the provided information is complete and correct, but this is done after the user has completed the entire application.

The system assumes that the Eligibility Address and Eligibility Programs (from Steps 2 and 4) are correct in order to filter IQ Programs for geographical location and income level. This allows the user to immediately see all available programs in their dashboard and make their selections.

After the application is completed by the user, the organization begins the process of verifying all uploads match the ID and Eligibility Programs they're supposed to. If more information is need or if there's a discrepancy, this can be handled manually by the [Platform Administrator](#platform-administrator) (by reaching out to the applicant).

## Verification Staff Process
This process doesn't begin until after the [user process](#user-process) is complete, in part so that the user process isn't interrupted by staff activity.

### User list view
The Get-Your 'user list' can be accessed from the 'Users' menu in the Get-Your [administration portal]. From here, [verification staff](#verification-staff) can access all newly-completed applicants by selecting the 'New Needs Verification' filter on the right sidenav. This limits the users to only those who are newly awaiting identification / Eligibility Program verification.

> ![NOTE]
> Other filter options are 'Awaiting Response' (only users who staff have marked as 'awaiting user response' (see [below](#administration-section))), 'All Needs Verification' (all users who needs verification, regardless of 'awaiting user response'), 'Has Been Verified' (only users who are marked as 'income has been verified'), and 'All' (no verification filter). See [Administration Portal] for additional details.

> ![NOTE]
> The default filter for the user list is 'By account disabled' > 'Not disabled', so all filters mentioned here are limited to only active accounts.

From the user list, staff will select a user via their hyperlink email address.

### User view
The resulting view contains pertinent information from the user. Only the user-verification ["happy path"](https://en.wikipedia.org/wiki/Happy_path) is included in this section; other cases can be found in [Troubleshooting].

> ![NOTE]
> Verification staff are part of a specific [authorization group] on the platform, and therefore will have the minimum privileges necessary to perform verifications. See [Authorization groups] for more details.

Once [Household Member section](#household-member-section) and [User Eligibility Programs section](#user-eligibility-programs-section) have been completed, verification staff will select the checkbox under 'INCOME HAS BEEN VERIFIED' in the 'HOUSEHOLD' section and save changes (via the 'SAVE' button at the bottom of the page). This will make the user visible for the [Program Coordinator process](#program-coordinator-process).

#### Administration section
The section titled 'ADMINISTRATION' is for use by internal staff, and will not be viewable by the user. Here, notes can be made about an account, as well as an account flagged as 'awaiting user response' (to be excluded from some user-list filters).

#### Household Member section
The section titled 'HOUSEHOLD MEMBER' shows all individuals in the user's household. Below each person is a link to the uploaded identification documentation for that person (or 'no document available' if it somehow doesn't exist); verification staff should verify that each ID matches the person it's linked to, that the birthdate is correct, and that at least one person's address matches the Eligibility Address in the 'ADDRESS' section (unless other accomodations have been made).

#### User Eligibility Programs section
The section titled 'USER ELIGIBILITY PROGRAMS' shows each program the user has selected, with link(s) to uploaded documents for each. Verification staff should verify that each uploaded document matches a member of the household.

## Program Coordinator Process
This process doesn't begin until after the [verification staff process](#verification-staff-process) is complete, so that [Program Coordinators](#program-coordinator) are using accurate user information.

This process doesn't exist on the platform yet (it's currently executed in the form of downloading data extracts and emailing them as CSVs to each Program Coordinator, via [a script in the `Get-Your-utils` repo](https://github.com/Get-Your/Get-Your-utils/blob/main/get_your_utils/python/run_extracts.py)), but it's planned to be similar to the [Verification Staff process](#verification-staff-process) but with each Program Coordinator having access only to enroll/unenroll users from their own program (using an as-yet-undefined Program Coordinator [authorization group]).

# Project Code Map
Here you will find architecture decisions around files and functions. All relative paths are in reference to the root repo folder (where this file is located).

> ![NOTE]
> Starting with v7.0.0, the code is formatted around the [`cookiecutter-django`](https://cookiecutter-django.readthedocs.io/en/latest) project. The structure differs significantly from the v6- code, although the function-level architecture is similar (if not exact).

After the [Configuration Files](#configuration-files) definitions are the portions of the Django project, which are separated into apps for responsibility segregation. Each subsection is an app in the project (located within 'get_your'), with further subsections as scripts within that app, then functions/classes (e.g. `app` > views > programs() is accessible to Django at `app.views.programs()` and can be found in the file tree at 'get_your/app/views.py > `programs()`')

> ![NOTE]
> Only the pertinent scripts/functions are called out here.

> ![NOTE]
> `models.py` for each app are not included here. The purpose of this document is to detail why the project is designed how it is; the models follow those design decisions.

## Configuration Files
These are the non-Django configurations files, such as for [Redis](https://github.com/redis/redis) and [Docker](https://docs.docker.com) containerization.

## `app`
This is the user-application part of the project.

## `dashboard`
This is the post-application user dashboard, which contains [IQ Program](#iq-programs) enrollment details, organization news, and user access to update (some of*) their information.

\* See [??????] for more details on what information can be updated after the application process and why.

## `files`
This is the portion of the project that handles file uploads.

## `monitor`
This part of the project handles project monitoring, specifically logging.

## `ref`
All reference data are within this part of the project.

## `users`
This part of the project handles users; it's a custom user model, created by `cookiecutter-django` and modified for use by Get-Your.

> ![IMPORTANT]
> This app is within the 'get_your' subdirectory, so the app name is actually `get_your.users`; it's shortened in the header for simplicity only.