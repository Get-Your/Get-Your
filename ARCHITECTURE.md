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