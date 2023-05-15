# -*- coding: utf-8 -*-
"""
Created on Fri May 12 08:48:56 2023

@author: TiCampbell

This script runs ETL on the v1 Get FoCo data to transform and port it to the
v2 Get Your database.

"""

# FILL NEW ADDRESSES TABLES --

# Current names: lookup table is application_addressesnew_rearch, user table
# is application_addresses_rearch.
# Place the same ID as the mailing and eligibility addresses for this initial
# fill.
# Field mapping is as such
# (application_addresses, application_addressesnew_rearch, application_addresses_rearch):
#     created, created_at, created_at
#     modified, modified_at, modified_at
#     user_id_id, NULL, user_id
#     address, address1, NULL
#     address2, address2, NULL
#     city, city, NULL
#     state, state, NULL
#     zipCode, zip_code, NULL
#     isInGMA, is_in_gma, NULL
#     isInGMA, is_city_covered, NULL
#     hasConnexion, has_connexion, NULL
#     is_verified, is_verified, NULL
#     NULL, id (auto-incremented), eligibility_address_id
#     NULL, id (auto-incremented), mailing_address_id

#When necessary: truncate addresses_new_rearch
#truncate table public.application_addressesnew_rearch cascade;

# Insert into the rearchitected lookup table
# Ensure all parts of the input addresses are uppercase (to match the .clean() function in the model)
insert into public.app_addressrd ("created_at", "modified_at", "address1", "address2", "city", "state", "zip_code", "is_in_gma", "is_city_covered", "has_connexion", "is_verified")
    select "created", "modified", UPPER("address"), UPPER("address2"), UPPER("city"), UPPER("state"), "zipCode", "isInGMA", "isInGMA", "hasConnexion", "is_verified"
    from public.application_addresses
    order by "created" asc
    on conflict do nothing;

# Gather user ID and lookup table ID to insert into addresses_rearch
insert into public.app_address ("created_at", "modified_at", "user_id", "eligibility_address_id", "mailing_address_id")
    select r."created_at", r."modified_at", o."user_id_id", r."id", r."id" from public.application_addressesnew_rearch r
        right join public.application_addresses o on 
        upper(o."address")=r."address1" and
        upper(o."address2")=r."address2" and
        upper(o."city")=r."city" and
        upper(o."state")=r."state" and
        o."zipCode"=r."zip_code";

# FILL NEW ELIGIBILITY TABLE --

# Current name: eligibility table is application_eligibility_rearch
# Field mapping is as such (application_eligibility, application_eligibility_rearch):
#     created, created_at
#     modified, modified_at
#     user_id_id, user_id
#     rent, duration_at_address
#     dependents, number_persons_in_household
#     <2021 or 2022>, depending on created date, ami_year
#     AmiRange_min, ami_range_min
#     AmiRange_max, ami_range_max
#     True if GenericQualified='ACTIVE' else False, is_income_verified

insert into public.app_household ("created_at", "modified_at", "user_id", "is_updated", "duration_at_address", "number_persons_in_household", "ami_range_min", "ami_range_max", "is_income_verified", "rent_own")
    select "created", "modified", "user_id_id", False, "rent", "dependents", "AmiRange_min", "AmiRange_max", (case when "GenericQualified"='ACTIVE' then true else false end), ''
    from public.application_eligibility;

# FILL NEW MOREINFO TABLE --

# Current name: application_moreinfo_rearch
# Field mapping is as such (application_moreinfo, application_moreinfo_rearch):
#     created, created_at
#     modified, modified_at
#     user_id_id, user_id
#     dependentInformation, household_info

# Truncate the (now-temporary) table first
truncate table public.application_moreinfo_rearch;

# Due to intensive conversions, the majority of this section needs to be run
# via Django. Follow the directions below:
print(
      """Run the ETL from MoreInfo via Django with the following:
1) Switch to branch `database-rearchitecture-p0-modifytable` in the GetFoco repo
2) Run the GetFoco app using `settings.local_<target_database>db` (you may need to `makemigrations`/`migrate` first)
3) Navigate to 127.0.0.1:8000/application/rearch_phase0 to write to public.application_moreinfo_rearch in the GetFoco database.
Continue this script to finish porting to GetYour."""
)

# modified_at is written automatically, so now we need to overwrite it from the temporary fields
update public.application_moreinfo_rearch set "created_at"="created_at_init_temp", "modified_at"="modified_at_init_temp";

## TODO: move public.application_moreinfo_rearch to public.app_householdmembers
## (directly, except for init_temp fields - ignore these completely)

# FILL IQ PROGRAMS TABLES --

## getfoco_dev.public.application_iqprogramqualifications_rearch has already
## been updated with the program information, so there's no need to revisit
## old tables

## TODO: Port getfoco_dev.public.application_iqprogramqualifications_rearch
## to public.app_iqprogramrd in *all environments*

# Current name: application_iq_programs_rearch
# Field mapping is as such (application_eligibility, application_iq_programs_rearch):
#     created, applied_at
#     '1970-01-01 00:00:00', enrolled_at (this will need to be updated via Python based on the historical income verification returned extracts)
#     user_id_id, user_id
#     for the rest, there isn't so much a field mapping as a loose connectivity that I'll recreate through this query

# Also need the ID from app_iqprogramrd
# Run for Connexion
insert into public.app_iqpgrogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
    select "created", '1970-01-01 00:00:00', "user_id_id", (case when "ConnexionQualified"='ACTIVE' then true else false end), (select id from public.app_iqprogramrd where program_name='connexion')
    from public.application_eligibility
    where "ConnexionQualified"='ACTIVE' or "ConnexionQualified"='PENDING';

# Run for Grocery Rebate
insert into public.app_iqpgrogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
    select "created", '1970-01-01 00:00:00', "user_id_id", (case when "GRqualified"='ACTIVE' then true else false end), (select id from public.app_iqprogramrd where program_name='grocery')
    from public.application_eligibility
    where "GRqualified"='ACTIVE' or "GRqualified"='PENDING';

# Run for Recreation
insert into public.app_iqpgrogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
    select "created", '1970-01-01 00:00:00', "user_id_id", (case when "RecreationQualified"='ACTIVE' then true else false end), (select id from public.app_iqprogramrd where program_name='recreation')
    from public.application_eligibility
    where "RecreationQualified"='ACTIVE' or "RecreationQualified"='PENDING';

# Run for SPIN
insert into public.app_iqpgrogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
    select "created", '1970-01-01 00:00:00', "user_id_id", (case when "SPINQualified"='ACTIVE' then true else false end), (select id from public.app_iqprogramrd where program_name='spin')
    from public.application_eligibility
    where "SPINQualified"='ACTIVE' or "SPINQualified"='PENDING';

# Run for defunct SPIN Community Pass
insert into public.app_iqpgrogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
    select "created", '1970-01-01 00:00:00', "user_id_id", (case when "SpinAccessQualified_depr"='ACTIVE' then true else false end), (select id from public.app_iqprogramrd where program_name='spin_community_pass')
    from public.application_eligibility
    where "SpinAccessQualified_depr"='ACTIVE' or "SpinAccessQualified_depr"='PENDING';

# FILL ELIGIBILITY PROGRAMS TABLES --

# Current name: application_programs_rearch
# There is no field mapping for this; everything until now has been hardcoded in Python

## getfoco_dev.public.application_programs_rearch has already been updated
## with the program information, so there's no need to revisit old tables

## TODO: Port getfoco_dev.public.application_programs_rearch
## to public.app_eligibilityprogramrd in *all environments*

# Current name: application_dashboard_form_rearch
# Field mapping is as such (dashboard_form, application_dashboard_form_rearch):
#     created, created_at
#     modified, modified_at
#     user_id_id, user_id
#     document, document_path
#     There's no direct mapping from dashboard_form to get the program_id, so I'm going to do it manually based on the unique document_title values *from PROD*

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='snap')
    from public.dashboard_form
    where document_title='SNAP';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='medicaid')
    from public.dashboard_form
    where document_title='Medicaid';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='free_reduced_lunch')
    from public.dashboard_form
    where document_title='Free and Reduced Lunch';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='identification')
    from public.dashboard_form
    where document_title='Identification';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='ebb_acf')
    from public.dashboard_form
    where document_title='ACP Letter';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='leap')
    from public.dashboard_form
    where document_title='LEAP Letter';

insert into public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
    select "created", "modified", "user_id_id", "document", (select id from public.app_eligibilityprogramrd where program_name='1040')
    from public.dashboard_form
    where document_title='1040' or document_title='1040 Form';