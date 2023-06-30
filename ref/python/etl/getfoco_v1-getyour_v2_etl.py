# -*- coding: utf-8 -*-
"""
Created on Fri May 12 08:48:56 2023

@author: TiCampbell

This script runs ETL on the v1 Get FoCo data to transform and port it to the
v2 Get Your database.

"""

from rich import print
from rich.progress import Progress
import psycopg2
import hashlib
import json
from decimal import Decimal
import warnings
import pendulum

import coftc_cred_man as crd

# NOTE that this is copied directly from getyour.app.build_hash on 2023-05-23.
# If the source changes, this function MUST be updated to match
def hash_address(address_dict: dict) -> str:
    """ 
    Create a SHA-1 hash from existing address values.
    :param address_dict: Dictionary of user-entered address fields.
    :returns str: String representation of SHA-1 address hash. SHA-1 hash is
        160 bits; written as hex for 40 characters.
    """
    # Explicitly define address field order
    keyList = ['address1', 'address2', 'city', 'state', 'zip_code']
    # Concatenate string representations of each value in sequence.
    # If value is string, convert to uppercase; if key DNE, use blank string.
    concatVals = ''.join(
        [address_dict[key].upper() if key in address_dict.keys() and isinstance(address_dict[key], str) \
         else str(address_dict[key]) if key in address_dict.keys() \
            else '' for key in keyList]
            )
    # Return SHA-1 hash of the concatenated strings
    return hashlib.sha1(bytearray(concatVals, 'utf8')).hexdigest()

def run_full_porting(profile):
    """
    Run all ETL, in order.

    Returns
    -------
    None.

    """
    
    print(
        "[bright_cyan]Updating new '{}' database with old data...".format(
            profile,
            )
        )

    global_objects = initialize_vars(profile)
    
    print(
        """[bold red]Before starting this process, confirm that\n
        - You've run [green]C:\\Users\\TiCampbell\\OneDrive - City of Fort Collins\\python\\get_foco\\sql\\v2_release\\initial_programrd_fills.sql[/green] against the {dbn} database\n
        - You've switched to branch [green]database-rearchitecture-p0-modifytable[/green] in the GetFoco repo and run [green]makemigrations[/green] then [green]migrate[/green] against the {dbo} database""".format(
            dbn=global_objects['cred_new'].config['db'],
            dbo=global_objects['cred_old'].config['db'],
            )
        )
    _ = input(": ")
    
    global_objects['current_user_offset'] = 100000
    update_current_users(global_objects)
    port_user(global_objects)
    port_address(global_objects)
    port_eligibility(global_objects)
    # Note that there is no corresponding eligibility history in PROD or STAGE
    port_householdmembers(global_objects)
    port_iqprograms(global_objects)
    port_eligibility_programs(global_objects)
    port_feedback(global_objects)
    
    verify_transfer(global_objects)
    
    add_missing_records(global_objects)
    update_income_values(global_objects)
    update_program_records(global_objects)
    
    global_objects['conn_old'].close()
    global_objects['conn_new'].close()
    
    print('[bright_cyan]Transfer to the new database complete!')

def initialize_vars(profile: str) -> dict:
    """
    Initialize variables for these imports

    Parameters
    ----------
    profile : str
        Name of the profile with correct database parameters.

    Returns
    -------
    dict
        Dictionary of initialization objects.

    """
    
    # Connect to new (v2) and old (v1) databases
    credOld = crd.Cred(f'{profile}_old')
    credNew = crd.Cred(f'{profile}')
    
    connOld = psycopg2.connect(
        "host={hst} user={usr} dbname={dbn} password={psw} sslmode={ssm}".format(
            hst=credOld.config['host'],
            usr=credOld.config['user'],
            dbn=credOld.config['db'],
            psw=credOld.password(),
            ssm='require')
        ) 
    
    connNew = psycopg2.connect(
        "host={hst} user={usr} dbname={dbn} password={psw} sslmode={ssm}".format(
            hst=credNew.config['host'],
            usr=credNew.config['user'],
            dbn=credNew.config['db'],
            psw=credNew.password(),
            ssm='require')
        ) 
    
    # Record the offset value for any current users
    currentUserOffset = 100000
    
    return(
        {
            'conn_new': connNew,
            'conn_old': connOld,
            'cred_new': credNew,
            'cred_old': credOld,
            'current_user_offset': currentUserOffset
            }
        )

def update_current_users(global_objects: dict) -> None:
    """
    0) Update any current users in the new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.

    """

    # MOVE ANY CURRENT USERS TO THE 100,000 BLOCK
    
    # Moving current users to some ridiculous user ID will ensure that inserted
    # users will preserve their current ID (making the porting much easier) and
    # allows removal and reinsertion of just the transferred users easier to
    # identify
    
    cursorNew = global_objects['conn_new'].cursor()
    
    # Warn if there are any existing user in non-dev databases
    if '_dev' not in global_objects['cred_new'].config['db']:
        cursorNew.execute("select count(*) from public.app_user")
        if cursorNew.fetchone()[0] > 0:
            raise Exception("There are already users in the app_user table!")
            
    # Update each table in order
    cursorNew.execute("update public.app_address set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_household set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_householdmembers set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_householdhist set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_iqprogram set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_eligibilityprogram set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=global_objects['current_user_offset']))
    cursorNew.execute("update public.app_user set id=id+{cradd} where id<{cradd}".format(cradd=global_objects['current_user_offset']))
    
    global_objects['conn_new'].commit()
    cursorNew.close()
    
def port_user(global_objects: dict) -> None:
    """
    1) Port 'user' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.

    """
    
    print("Beginning user port...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()
    
    # FILL NEW USERS TABLE --
    
    # Current name: users table is application_user
    # All fields transfer directly over *except* `created` and `modified`, which
    # were removed in v2 because they duplicate the functionality of Django's
    # internal `date_joined` and `last_login`, respectively.
    
    cursorOld.execute("""SELECT "id", "password", "last_login", "is_superuser", "is_staff", "is_active", "date_joined", "email", "first_name", "last_name", "phone_number", false, "is_archived", false
                      from public.application_user""")
    userList = cursorOld.fetchall()
    
    if len(userList) > 0:
        cursorNew.execute("""insert into public.app_user ("id", "password", "last_login", "is_superuser", "is_staff", "is_active", "date_joined", "email", "first_name", "last_name", "phone_number", "has_viewed_dashboard", "is_archived", "is_updated")
                          VALUES {}""".format(
                ', '.join(['%s']*len(userList))
                ),
            userList,
            )
        
        global_objects['conn_new'].commit()
        
    # Set autoincrement sequence to continue after the last record (this will
    # account for offset users as well)
    tableName = 'app_user'
    sequenceColumn = 'id'
    cursorNew.execute(
        """select max({col}) from public.{tbl}""".format(
            tbl=tableName,
            col=sequenceColumn,
            )
        )
    maxVal = cursorNew.fetchone()[0]
    
    # Set the last value of the sequence to maxVal and advance for the next
    # insert
    cursorNew.execute(
        """SELECT setval('{tbl}_{col}_seq', {mxv})""".format(
            tbl=tableName,
            col=sequenceColumn,
            mxv=maxVal,
            )
        )
    global_objects['conn_new'].commit()
        
    cursorNew.close()
    cursorOld.close()    
    
    print("User port complete")
    
def port_address(global_objects: dict) -> None:
    """
    2) Port 'address' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning address port...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()

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

    # Insert into the rearchitected lookup table
    # Ensure all parts of the input addresses are uppercase (to match the
    # .clean() function in the model).
    # Note that isInGMA is selected twice; for is_in_gma and is_city_covered
    # Note that address_sha1 will be appended to the end
    
    # fieldConversionList (<old name>, <new name>) is necessary for this
    # because a SHA-1 hash is going to be calculated from the included fields
    # Note that these fields are selected at the *beginning* of the query
    fieldConversionList = [
        ('address', 'address1'),
        ('address2', 'address2'),
        ('city', 'city'),
        ('state', 'state'),
        ('zipCode', 'zip_code'),
        ]
    cursorOld.execute("""SELECT {fd}, "created", "modified", "isInGMA", "isInGMA", "hasConnexion", "is_verified"
        from public.application_addresses
        order by "created" asc""".format(
            fd=', '.join([f'UPPER("{x[0]}")' if x[0]!='zipCode' else f'"{x[0]}"' for x in fieldConversionList]),
            )
    )
    addressList = cursorOld.fetchall()
    
    if len(addressList) > 0:
        # Add the address hash to each addressList element
        outAddressList = []
        for idxitm,addritm in enumerate(addressList):
            
            # Create dictionary of element 1 of fieldConversionList
            addressDict = {
                key[1]: addritm[idx] for idx,key in enumerate(fieldConversionList)
                }
            
            # Hash the address and append to addressList (need to recreate tuple)
            outAddressList.append(tuple(list(addritm)+[hash_address(addressDict)]))
            
        # Verify that all addresses were converted to outAddressList in order
        verifyList = [x==y[:-1] for x,y in zip(addressList,outAddressList)]
        assert all(verifyList)
    
        # Loop through each record instead of a single statement with multiple
        # records so that the ON CONFLICT UPDATE clause can work properly even
        # for multiple source records
        for addritm in outAddressList:
            # The special 'excluded' table contains the conflicting insertion
            # records. For these nullable Boolean records, Postgres OR works as
            # such (in order of descending truthiness): TRUE > NULL > FALSE
            cursorNew.execute("""insert into public.app_addressrd ("{fd}", "created_at", "modified_at", "is_in_gma", "is_city_covered", "has_connexion", "is_verified", "address_sha1")
                              VALUES ({vl})
                              ON CONFLICT (address_sha1) DO
                                  UPDATE SET is_in_gma=app_addressrd.is_in_gma OR excluded.is_in_gma,
                                  is_city_covered=app_addressrd.is_city_covered OR excluded.is_city_covered,
                                  has_connexion=app_addressrd.has_connexion OR excluded.has_connexion""".format(
                    fd='", "'.join([x[1] for x in fieldConversionList]),
                    vl=', '.join(['%s']*len(addritm))
                    ),
                addritm,
                )
            
        global_objects['conn_new'].commit()
    
        # Gather user ID and lookup table ID to insert into addresses_rearch
        usrFields = [
            'created',
            'modified',
            'user_id_id',
            ]
        cursorOld.execute(
            """SELECT {adfd}, {usrfd} from public.application_addresses""".format(
                adfd=', '.join([f'UPPER("{x[0]}")' if x[0]!='zipCode' else f'"{x[0]}"' for x in fieldConversionList]),
                usrfd=', '.join([f'"{x}"' for x in usrFields])
                )
        )
        userAddressList = cursorOld.fetchall()
        
        # Loop through each userAddressList item, gather the ID from app_addressrd,
        # and insert into app_address
        for usritm in userAddressList:
            
            # Create dictionary of element 1 of fieldConversionList
            addressDict = {
                key[1]: usritm[idx] for idx,key in enumerate(fieldConversionList)
                }
            
            cursorNew.execute("""SELECT "id" FROM public.app_addressrd WHERE "address_sha1"=%s""", (hash_address(addressDict), ))
            idVal = cursorNew.fetchone()[0]
            
            cursorNew.execute("""INSERT INTO public.app_address ("created_at", "modified_at", "user_id", "eligibility_address_id", "mailing_address_id", "is_updated")
                              VALUES ({})""".format(
                              ', '.join(['%s']*(len(usrFields)+3))
                              ),
                        list(usritm[-len(usrFields):])+[idVal, idVal, False],
                        )

        global_objects['conn_new'].commit()
        
    # Set autoincrement sequence to continue after the last record
    tableName = 'app_addressrd'
    sequenceColumn = 'id'
    cursorNew.execute(
        """select max({col}) from public.{tbl}""".format(
            tbl=tableName,
            col=sequenceColumn,
            )
        )
    maxVal = cursorNew.fetchone()[0]
    
    # Set the last value of the sequence to maxVal and advance for the next
    # insert
    cursorNew.execute(
        """SELECT setval('{tbl}_{col}_seq', {mxv})""".format(
            tbl=tableName,
            col=sequenceColumn,
            mxv=maxVal,
            )
        )
    global_objects['conn_new'].commit()
            
    cursorNew.close()
    cursorOld.close()  
    
    print("Address port complete")
    
def port_eligibility(global_objects: dict) -> None:
    """
    3) Port 'eligibility' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning eligibility port...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()

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
    

    cursorOld.execute("""SELECT "created", "modified", "user_id_id", False, (CASE WHEN "rent" NOT IN ('Rent', 'Own') THEN "rent" ELSE '' END), "dependents", "AmiRange_max", (CASE WHEN "GenericQualified"='ACTIVE' THEN true ELSE false END), (CASE WHEN "rent" IN ('Rent', 'Own') THEN LOWER("rent") ELSE '' END) FROM public.application_eligibility""")
    eligList = cursorOld.fetchall()
    
    if len(eligList) > 0:
        cursorNew.execute("""insert into public.app_household ("created_at", "modified_at", "user_id", "is_updated", "duration_at_address", "number_persons_in_household", "income_as_fraction_of_ami", "is_income_verified", "rent_own")
                          VALUES {}""".format(
                ', '.join(['%s']*len(eligList))
                ),
            eligList,
            )
        
        global_objects['conn_new'].commit()
        
    cursorNew.close()
    cursorOld.close()   
    
    print("Eligibility port complete")
    
def port_householdmembers(global_objects: dict) -> None:
    """
    4) Port 'householdmembers' from old to new database.
    
    Note that this section *does* use the Phase 0 '_rearch' table as a
    temporary conversion table (out of convenience).

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning householdmembers port...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()

    # FILL NEW MOREINFO TABLE --
    
    # Current name: application_moreinfo_rearch
    # Field mapping is as such (application_moreinfo, application_moreinfo_rearch):
    #     created, created_at
    #     modified, modified_at
    #     user_id_id, user_id
    #     dependentInformation, household_info
    
    # Truncate the (now-temporary) table first
    cursorOld.execute("""truncate table public.application_moreinfo_rearch""")
    global_objects['conn_old'].commit()
    
    # Due to intensive conversions, the majority of this section needs to be run
    # via Django. Follow the directions below:
    print(
          """\nRun the ETL from MoreInfo via Django with the following:
    1) Switch to branch [green]database-rearchitecture-p0-modifytable[/green] in the GetFoco repo
    2) Run the GetFoco app using [green]settings.local_{tdb}db[/green]
    3) Navigate to 127.0.0.1:8000/application/rearch_phase0 to write to public.application_moreinfo_rearch in the GetFoco database. When the page loads, this step is complete.
    Continue this script to finish porting to GetYour.\n""".format(
        tdb=global_objects['cred_new'].config['db'].split('_')[-1],
        )
    )
    _ = input("Press any key to continue (when this is complete). ")
    
    
    # modified_at is written automatically, so now we need to overwrite it from the temporary fields
    cursorOld.execute(
        """update public.application_moreinfo_rearch set "created_at"="created_at_init_temp", "modified_at"="modified_at_init_temp" """
        )
    global_objects['conn_old'].commit()
    
    # Move public.application_moreinfo_rearch to public.app_householdmembers
    # (directly, except for init_temp fields - ignore these completely)
    cursorOld.execute("""SELECT "created_at", "modified_at", "user_id", "household_info", false FROM public.application_moreinfo_rearch""")
    membersList = cursorOld.fetchall()
    
    if len(membersList) > 0:
        cursorNew.execute("""insert into public.app_householdmembers ("created_at", "modified_at", "user_id", "household_info", "is_updated")
                          VALUES {}""".format(
                ', '.join(['%s']*len(membersList))
                ),
            # Serialize the JSON in membersList
            [tuple([json.dumps(y) if idx==len(x)-2 else y for idx,y in enumerate(x)]) for x in membersList],
            )
    
        global_objects['conn_new'].commit()
        
    cursorNew.close()
    cursorOld.close()   
    
    print("Householdmembers port complete")
    
def port_iqprograms(global_objects: dict) -> None:
    """
    5) Port 'iq programs' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    def update_program(global_objects, program_name, old_field_name):
        cursorOld = global_objects['conn_old'].cursor()
        cursorNew = global_objects['conn_new'].cursor()
        
        # FILL IQ PROGRAMS TABLES --
        
        ## getfoco_dev.public.application_iqprogramqualifications_rearch has already
        ## been updated with the program information, so there's no need to revisit
        ## old tables
        
        # Current name: application_iq_programs_rearch
        # Field mapping is as such (application_eligibility, application_iq_programs_rearch):
        #     created, applied_at
        #     '1970-01-01 00:00:00', enrolled_at (this will need to be updated via Python based on the historical income verification returned extracts)
        #     user_id_id, user_id
        #     for the rest, there isn't so much a field mapping as a loose connectivity that I'll recreate through this query
        
        # Pull the users in this program
        cursorOld.execute(
            """SELECT "created", '1970-01-01 00:00:00', "user_id_id", (CASE WHEN "{fdn}"='ACTIVE' THEN true ELSE false END) FROM public.application_eligibility WHERE "{fdn}"='ACTIVE' or "{fdn}"='PENDING'""".format(
                fdn=old_field_name,
                )
            )
        programList = cursorOld.fetchall()
        
        # Add the new program ID from iqprogramrd to the end of each programList
        # element
        cursorNew.execute(
            """SELECT "id" FROM public.app_iqprogramrd WHERE "program_name"='{pnm}'""".format(
                pnm=program_name,
                )
            )
        idVal = cursorNew.fetchone()[0]
        programList = [tuple(list(x)+[idVal]) for x in programList]
        
        # Insert into the new table
        if len(programList) > 0:
            cursorNew.execute("""INSERT INTO public.app_iqprogram ("applied_at", "enrolled_at", "user_id", "is_enrolled", "program_id")
                              VALUES {}""".format(
                    ', '.join(['%s']*len(programList))
                    ),
                programList,
                )
            
            global_objects['conn_new'].commit()
            
        cursorNew.close()
        cursorOld.close() 

    print("Beginning iqprograms port...")
    
    # Run for Connexion
    update_program(global_objects, 'connexion', 'ConnexionQualified')
    print("Connexion port complete")
    
    # Run for Grocery Rebate
    update_program(global_objects, 'grocery', 'GRqualified')
    print("Grocery port complete")
    
    # Run for Recreation
    update_program(global_objects, 'recreation', 'RecreationQualified')
    print("Recreation port complete")
    
    # Run for SPIN
    update_program(global_objects, 'spin', 'SPINQualified')
    print("SPIN port complete")
    
    # Run for defunct SPIN Community Pass
    update_program(global_objects, 'spin_community_pass', 'SpinAccessQualified_depr')
    print("SPIN Community Pass port complete")
    
    # Set autoincrement sequence to continue after the last record
    cursorNew = global_objects['conn_new'].cursor()
    tableName = 'app_iqprogram'
    sequenceColumn = 'id'
    cursorNew.execute(
        """select max({col}) from public.{tbl}""".format(
            tbl=tableName,
            col=sequenceColumn,
            )
        )
    maxVal = cursorNew.fetchone()[0]
    
    # Set the last value of the sequence to maxVal and advance for the next
    # insert
    cursorNew.execute(
        """SELECT setval('{tbl}_{col}_seq', {mxv})""".format(
            tbl=tableName,
            col=sequenceColumn,
            mxv=maxVal,
            )
        )
    global_objects['conn_new'].commit()
    
    cursorNew.close()
    
    print("All iqprograms port complete")
    
def port_eligibility_programs(global_objects: dict) -> None:
    """
    6) Port 'eligibility program' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    def update_documents(global_objects, program_name, document_title):
        cursorOld = global_objects['conn_old'].cursor()
        cursorNew = global_objects['conn_new'].cursor()
        
        # FILL ELIGIBILITY PROGRAMS TABLES --
        
        # Current name: application_dashboard_form_rearch
        # Field mapping is as such (dashboard_form, application_dashboard_form_rearch):
        #     created, created_at
        #     modified, modified_at
        #     user_id_id, user_id
        #     document, document_path
        #     There's no direct mapping from dashboard_form to get the program_id, so I'm going to do it manually based on the unique document_title values *from PROD*
            
        # Pull the users' documents
        cursorOld.execute(
            """SELECT "created", "modified", "user_id_id", "document" FROM public.dashboard_form WHERE "document_title"='{dct}'""".format(
                dct=document_title,
                )
            )
        documentList = cursorOld.fetchall()
        
        # Add the new program ID from iqprogramrd to the end of each programList
        # element
        cursorNew.execute(
            """SELECT "id" FROM public.app_eligibilityprogramrd WHERE "program_name"='{pnm}'""".format(
                pnm=program_name,
                )
            )
        idVal = cursorNew.fetchone()[0]
        documentList = [tuple(list(x)+[idVal]) for x in documentList]
        
        # Insert into the new table
        if len(documentList) > 0:
            cursorNew.execute("""INSERT INTO public.app_eligibilityprogram ("created_at", "modified_at", "user_id", "document_path", "program_id")
                              VALUES {}""".format(
                    ', '.join(['%s']*len(documentList))
                    ),
                documentList,
                )
            
            global_objects['conn_new'].commit()
            
        cursorNew.close()
        cursorOld.close() 

    print("Beginning eligibility programs port...")
    
    # Run for SNAP
    update_documents(global_objects, 'snap', 'SNAP')
    print("SNAP documents complete")
    
    # Run for Medicaid
    update_documents(global_objects, 'medicaid', 'Medicaid')
    print("Medicaid documents complete")
    
    # Run for Free and Reduced Lunch
    update_documents(global_objects, 'free_reduced_lunch', 'Free and Reduced Lunch')
    print("Free and Reduced Lunch documents complete")
    
    # Run for Identification
    update_documents(global_objects, 'identification', 'Identification')
    print("Identification documents complete")
    
    # Run for ACP
    update_documents(global_objects, 'ebb_acf', 'ACP Letter')
    print("ACP documents complete")
    
    # Run for LEAP
    update_documents(global_objects, 'leap', 'LEAP Letter')
    print("LEAP documents complete")
    
    # Run twice for 1040 (different titles)
    update_documents(global_objects, '1040', '1040')
    update_documents(global_objects, '1040', '1040 Form')
    print("1040 documents complete")

    print("All eligibility programs port complete")    
    
    
def port_feedback(global_objects: dict) -> None:
    """
    3) Port 'feedback' from old to new database.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning user feedback port...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()

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
    

    cursorOld.execute("""SELECT "id", "created", "modified", "feedbackComments", "starRating" FROM public.dashboard_feedback""")
    feedbackList = cursorOld.fetchall()
    
    if len(feedbackList) > 0:
        cursorNew.execute("""insert into public.app_feedback ("id", "created", "modified", "feedback_comments", "star_rating")
                          VALUES {}""".format(
                ', '.join(['%s']*len(feedbackList))
                ),
            feedbackList,
            )
        
        global_objects['conn_new'].commit()
        
    # Set autoincrement sequence to continue after the last record
    tableName = 'app_feedback'
    sequenceColumn = 'id'
    cursorNew.execute(
        """select max({col}) from public.{tbl}""".format(
            tbl=tableName,
            col=sequenceColumn,
            )
        )
    maxVal = cursorNew.fetchone()[0]
    
    # Set the last value of the sequence to maxVal and advance for the next
    # insert
    cursorNew.execute(
        """SELECT setval('{tbl}_{col}_seq', {mxv})""".format(
            tbl=tableName,
            col=sequenceColumn,
            mxv=maxVal,
            )
        )
    global_objects['conn_new'].commit()
        
    cursorNew.close()
    cursorOld.close()   
    
    print("User feedback port complete")
    
    
def verify_transfer(global_objects: dict) -> None:
    """
    Verify the proper transfer of all data.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning verification...")
    print("\nNOTE THAT app_householdmembers WILL NEED TO BE MANUALLY SPOTCHECKED\n\n")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()

    cursorOld.execute("""SELECT "id" from public.application_user order by "id" asc""")
    oldIdList = [x[0] for x in cursorOld.fetchall()]
    
    cursorNew.execute(
        """SELECT "id" from public.app_user where "id"<{curadd} order by "id" asc""".format(
            curadd=global_objects['current_user_offset']))
    newIdList = [x[0] for x in cursorNew.fetchall()]
    
    # Verify the lists are equal
    assert oldIdList==newIdList
    
    # Remove the beginning of newIdList in case of error
    # removeIdUntil=276; newIdList=[x for x in newIdList if x>=removeIdUntil]
    
    with Progress() as progress:
    
        verifyTask = progress.add_task(
            "[bright_cyan]Verifying...",
            total=len(newIdList),
            )
    
        try:
            maxIdx = len(newIdList)
            # Loop through all users < global_objects['current_user_offset']
            for idx,usrid in enumerate(newIdList):
                
                # Set the index that previously errored out
                previousErrorIdx = 0
                if idx < previousErrorIdx:
                    progress.update(verifyTask, advance=1)
                    continue
                
                # Reset program_name so as not to confuse error messaging
                program_name = ''
                
                ## Address
                currentTest = 'address'
                fieldConversionList = [
                    # Skip dates, since addresses are combined above into the
                    # addressrd using the newest version (so either would likely
                    # error out)
                    # ('created', 'created_at'),
                    # ('modified', 'modified_at'),
                    ('address', 'address1'),
                    ('address2', 'address2'),
                    ('city', 'city'),
                    ('state', 'state'),
                    ('zipCode', 'zip_code'),
                    ('is_verified', 'is_verified'),
                    ('isInGMA', 'is_in_gma'),
                    ('isInGMA', 'is_city_covered'),
                    ('hasConnexion', 'has_connexion'),
                    ]
                
                cursorOld.execute(
                    """select {fd} from public.application_addresses where "user_id_id"={usr}""".format(
                        fd=', '.join([f'UPPER("{x[0]}")' if x[0] in ('address', 'address2', 'city', 'state') else f'"{x[0]}"' for x in fieldConversionList]),
                        usr=usrid,
                        )
                    )
                oldRec = cursorOld.fetchall()
                
                cursorNew.execute(
                    """select r."{fd}" from public.app_addressrd r 
                    inner join public.app_address a on a."eligibility_address_id"=r."id" 
                    where a."user_id"={usr}""".format(
                        fd='", r."'.join([x[1] for x in fieldConversionList]),
                        usr=usrid,
                        )
                    )
                newRec = cursorNew.fetchall()
                
                if len(oldRec)>0 or len(newRec)>0:
                    # Verify all non-Boolean-lookup values match
                    assert oldRec[0][:-3]==newRec[0][:-3]
                    
                    # Verify that the final 3 values are truthier in newRec than oldRec
                    # True > False > None
                    assert all([True if (y==True and (x==False or x is None)) or (y==False and x is None) else y==x for x,y in zip(oldRec[0][-3:], newRec[0][-3:])])
                
                ## Household
                currentTest = 'household'
                fieldConversionList = [
                    ('"created"', 'created_at'),
                    ('"modified"', 'modified_at'),
                    ("""(CASE WHEN "rent" NOT IN ('Rent', 'Own') THEN "rent" ELSE '' END)""", 'duration_at_address'),
                    ('"dependents"', 'number_persons_in_household'),
                    ('"AmiRange_max"', 'income_as_fraction_of_ami'),
                    ("""(CASE WHEN "GenericQualified"='ACTIVE' THEN true ELSE false END)""", 'is_income_verified'),
                    ("""(CASE WHEN "rent" IN ('Rent', 'Own') THEN LOWER("rent") ELSE '' END)""", 'rent_own'),
                    ]
                
                cursorOld.execute(
                    """select {fd} from public.application_eligibility where "user_id_id"={usr}""".format(
                        fd=', '.join([x[0] for x in fieldConversionList]),
                        usr=usrid,
                        )
                    )
                oldRec = cursorOld.fetchall()
                
                cursorNew.execute(
                    """select "{fd}" from public.app_household 
                    where "user_id"={usr}""".format(
                        fd='", "'.join([x[1] for x in fieldConversionList]),
                        usr=usrid,
                        )
                    )
                newRec = cursorNew.fetchall()
                
                # Verify all values match
                assert oldRec==newRec
                
                ## IQ programs
                currentTest = 'iq programs'
                programList = [
                    ('connexion', 'ConnexionQualified'),
                    ('grocery', 'GRqualified'),
                    ('recreation', 'RecreationQualified'),
                    ('spin', 'SPINQualified'),
                    ('spin_community_pass', 'SpinAccessQualified_depr'),
                    ]
                for program_name, old_field_name in programList:
                    fieldConversionList = [
                        ('created', 'applied_at'),
                        ("""(CASE WHEN "{fdn}"='ACTIVE' THEN true ELSE false END)""".format(fdn=old_field_name), 'is_enrolled'),
                        ]
                    
                    cursorOld.execute(
                        """select {fd} from public.application_eligibility where "user_id_id"={usr} and ("{fdn}"='ACTIVE' or "{fdn}"='PENDING')""".format(
                            fd=', '.join([x[0] for x in fieldConversionList]),
                            usr=usrid,
                            fdn=old_field_name,
                            )
                        )
                    oldRec = cursorOld.fetchall()
                    
                    # Gather the program ID
                    cursorNew.execute(
                        """SELECT "id" FROM public.app_iqprogramrd WHERE "program_name"='{pnm}'""".format(
                            pnm=program_name,
                            )
                        )
                    programId = cursorNew.fetchone()[0]
                    
                    cursorNew.execute(
                        """select "{fd}" from public.app_iqprogram 
                        where "user_id"={usr} and "program_id"={prid}""".format(
                            fd='", "'.join([x[1] for x in fieldConversionList]),
                            usr=usrid,
                            prid=programId,
                            )
                        )
                    newRec = cursorNew.fetchall()
                    
                    # Verify all values match
                    assert oldRec==newRec
                    
                ## Eligibility programs
                currentTest = 'eligibility programs'
                fieldConversionList = [
                    ('created', 'created_at'),
                    ('modified', 'modified_at'),
                    ('document', 'document_path'),
                    ]
                
                documentsList = [
                    ('snap', ('SNAP',)),
                    ('medicaid', ('Medicaid',)),
                    ('free_reduced_lunch', ('Free and Reduced Lunch',)),
                    ('identification', ('Identification',)),
                    ('ebb_acf', ('ACP Letter',)),
                    ('leap', ('LEAP Letter',)),
                    ('1040', ('1040', '1040 Form')),
                    ]
                for program_name, document_titles in documentsList:
                    cursorOld.execute(
                        """select "{fd}" from public.dashboard_form where "user_id_id"={usr} and ({dct}) order by "{crf}" """.format(
                            fd='", "'.join([x[0] for x in fieldConversionList]),
                            crf=fieldConversionList[0][0],
                            usr=usrid,
                            dct=' or '.join([f""""document_title"='{x}'""" for x in document_titles]),
                            )
                        )
                    oldRec = cursorOld.fetchall()
                    
                    # Gather the program ID
                    cursorNew.execute(
                        """SELECT "id" FROM public.app_eligibilityprogramrd WHERE "program_name"='{pnm}'""".format(
                            pnm=program_name,
                            )
                        )
                    programId = cursorNew.fetchone()[0]
                    
                    cursorNew.execute(
                        """select "{fd}" from public.app_eligibilityprogram
                        where "user_id"={usr} and "program_id"={prid} order by "{crf}" """.format(
                            fd='", "'.join([x[1] for x in fieldConversionList]),
                            crf=fieldConversionList[0][1],
                            usr=usrid,
                            prid=programId,
                            )
                        )
                    newRec = cursorNew.fetchall()
                    
                    # Verify all values match
                    assert oldRec==newRec
        
                progress.update(verifyTask, advance=1)
                    
        except AssertionError:
            raise AssertionError(
                "Error at ID {idv} (index {idxv}): {curt} ({prg})".format(
                    idxv=idx,
                    idv=usrid,
                    curt=currentTest,
                    prg=program_name,
                    )
                )
            
    # Verify proper user feedback migration. This isn't connected to users, so
    # it's done in its own section
    cursorOld.execute("""SELECT "id", "created", "modified", "feedbackComments", "starRating" FROM public.dashboard_feedback order by "id" asc""")
    oldFeedbackList = cursorOld.fetchall()
    
    cursorNew.execute("""SELECT "id", "created", "modified", "feedback_comments", "star_rating" from public.app_feedback order by "id" asc""")
    newFeedbackList = cursorNew.fetchall()
    
    # Verify the lists are equal
    assert oldFeedbackList==newFeedbackList

    cursorNew.close()
    cursorOld.close() 
    
    print('ALL FEEDBACK AND {} USERS VERIFIED'.format(maxIdx-1))
    
    
def add_missing_records(global_objects: dict) -> None:
    """
    Add missing 'identification' file records to the v2 data model.
    
    This issue is caused by program names being hardcoded into the v1.x app:
    the app would identify when users needed to upload their ID and it
    therefore wouldn't be stored in the database for us to port. This function
    adds a blank ID field to each user that doesn't already have an ID upload
    field.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning addition of missing identification records...")
    
    cursorOld = global_objects['conn_old'].cursor()
    cursorNew = global_objects['conn_new'].cursor()
    
    # Collect all users *in app_eligibility* (meaning they have at least one
    # program selected)
    cursorNew.execute("select distinct user_id from public.app_eligibilityprogram where user_id not in (select distinct user_id from public.app_eligibilityprogram where program_id=1) order by user_id")
    missingRecUsers = [x[0] for x in cursorNew.fetchall()]
    
    # Loop through each user and add the missing ID record (with generic
    # timestamps)
    for usrid in missingRecUsers:
        cursorNew.execute(
            """INSERT INTO public.app_eligibilityprogram (created_at, modified_at, document_path, program_id, user_id) 
            VALUES ('1970-01-01T00:00:00-0000', '1970-01-01T00:00:00-0000', '', 1, %s)""",
            (usrid,),
            )
        
    global_objects['conn_new'].commit()
    
    # Verify that each user in the eligibilityprogram table has exactly one
    # ID record
    # ACTUALLY this won't work because users have uploaded multiple ID file
    # records (erroneous), so use this instead:
        # Verify that each user in the eligibilityprogram table has *at least
        # one* eligibility record AND no more than one record if any have an
        # empty document_path
        
    # Ensure each user has at least one ID record
    cursorNew.execute("select count(*) from public.app_eligibilityprogram where program_id=1 group by user_id")
    perUserCount = [x[0] for x in cursorNew.fetchall()]
    assert all(True for x in perUserCount if x>0)
    
    # Ensure each user with a blank ID upload has *only* one ID record
    cursorNew.execute(
        """select count(*) from public.app_eligibilityprogram where program_id=1 and user_id in (
            select distinct user_id from public.app_eligibilityprogram where program_id=1 and document_path=''
        ) group by user_id"""
    )
    blankUserCount = [x[0] for x in cursorNew.fetchall()]
    assert len(blankUserCount) == sum(blankUserCount)

    print('Missing identification records successfully added')
    
    # Set autoincrement sequence to continue after the last record
    tableName = 'app_eligibilityprogram'
    sequenceColumn = 'id'
    cursorNew.execute(
        """select max({col}) from public.{tbl}""".format(
            tbl=tableName,
            col=sequenceColumn,
            )
        )
    maxVal = cursorNew.fetchone()[0]
    
    # Set the last value of the sequence to maxVal and advance for the next
    # insert
    cursorNew.execute(
        """SELECT setval('{tbl}_{col}_seq', {mxv})""".format(
            tbl=tableName,
            col=sequenceColumn,
            mxv=maxVal,
            )
        )
    global_objects['conn_new'].commit()

    cursorNew.close()
    cursorOld.close() 


def update_income_values(global_objects: dict) -> None:
    """
    For non-income-verified applicants using the v1 app (i.e. before this ETL
    is run), income_as_fraction_of_ami was self-selected, which means it may
    not match the Eligibility Program selection. The v2 extract won't include
    income at all, so these values need to be updated to match the selected
    Eligibility Programs.
    
    ALSO, v2 doesn't store income values until all necessary files are
    uploaded, so remove the value if there are blank "document_path" for any
    user.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning update of income values...")
    warnings.warn("WARNING: there is no verification for this section")
    
    cursorNew = global_objects['conn_new'].cursor()
    
    # Collect all users who haven't been income-verified
    cursorNew.execute(
        """select user_id from public.app_household
        where is_income_verified=false order by user_id""")
    nonVerifiedUsers = [x[0] for x in cursorNew.fetchall()]
    
    # Collect all programs with auto-apply enabled
    cursorNew.execute(
        """select id, ami_threshold from public.app_iqprogramrd where enable_autoapply=true"""
        )
    autoApplyIdThreshold = cursorNew.fetchall()
    
    # Loop through each user and 
    # a) remove the income_as_fraction value if they have un-uploaded files or
    # b) use the app logic to find the minimum AMI and update their income value
    
    with Progress() as progress:
    
        updateTask = progress.add_task(
            "[bright_cyan]Updating...",
            total=len(nonVerifiedUsers),
            )
        
        for usrid in nonVerifiedUsers:
            # Check for user not in table or missing files (blank document_path)
            cursorNew.execute(
                """select distinct p.user_id, m.missing_count from public.app_eligibilityprogram p 
                    left join public.app_eligibilityprogramrd r on r.id=p.program_id
                    left join (select ip.user_id, count(*) as missing_count from public.app_eligibilityprogram ip 
                        left join public.app_eligibilityprogramrd ir on ir.id=ip.program_id 
                        where ir.is_active=true and ip.document_path='' 
                        group by ip.user_id) m on m.user_id=p.user_id 
                    where r.is_active=true and p.user_id={}""".format(
                usrid,
                )
            )
            # Output will be None if no user; (user_id, not None) if missing files;
            # (user_id, None) if no missing files
            userMissingFilesCount = cursorNew.fetchone()
            
            if userMissingFilesCount is None or userMissingFilesCount[1] is not None:
                # If the user doesn't exist in eligibilityprograms or there are
                # missing files, remove the income value
                cursorNew.execute(
                    """update public.app_household set income_as_fraction_of_ami=null where user_id={}""".format(
                        usrid,
                        )
                    )
                
            else:
                # If there are no missing files (and therefore the user exists),
                # find the minimum AMI of the selected programs
                cursorNew.execute(
                    """select min(ami_threshold) from public.app_eligibilityprogram p 
                    left join public.app_eligibilityprogramrd r on r.id=p.program_id 
                    where r.is_active=true and user_id={}""".format(
                    usrid,
                    )
                )
                minAmi = cursorNew.fetchone()[0]
            
                if minAmi == Decimal('1'):
                    # The two "programs" with ami_threshold==1 are Identification
                    # (id==1) and 1040 (id==2). If there is no program_id==2,
                    # update the income value, else leave it alone
                    cursorNew.execute(
                        """select count(*) from public.app_eligibilityprogram 
                        where user_id={} and program_id=2""".format(
                        usrid,
                        )
                    )
                    has1040 = cursorNew.fetchone()[0]
                    
                    if has1040 == 0:
                        cursorNew.execute(
                            """update public.app_household set income_as_fraction_of_ami=%s where user_id={}""".format(
                                usrid,
                                ),
                            (minAmi,),
                            )
                        
                else:
                    # If minAmi < 1, update the income value with minAmi
                    cursorNew.execute(
                        """update public.app_household set income_as_fraction_of_ami=%s where user_id={}""".format(
                            usrid,
                            ),
                        (minAmi,),
                        )
                    
                    # Go through all auto-apply and auto-apply each user for any
                    # programs they qualify for and aren't already applied/enrolled
                    for prgmid, prgmthreshold in autoApplyIdThreshold:
                        cursorNew.execute(
                            """select count(*) from public.app_iqprogram where user_id={uid} and program_id={pid}""".format(
                                uid=usrid,
                                pid=prgmid,
                                )
                            )
                        recCount = cursorNew.fetchone()[0]
                        
                        # Compare minAmi and the program threshold if there isn't a
                        # record for this user+program
                        if recCount == 0:
                            if minAmi <= prgmthreshold:
                                cursorNew.execute(
                                    """insert into public.app_iqprogram ("applied_at", "is_enrolled", "program_id", "user_id") 
                                    VALUES ({})""".format(
                                        ', '.join(['%s']*4)
                                        ),
                                    (pendulum.now(), False, prgmid, usrid),
                                    )
    
            progress.update(updateTask, advance=1)
        
    global_objects['conn_new'].commit()
    
    ## Verify that all auto-apply programs have only one record per user
    for prgmid, prgmthreshold in autoApplyIdThreshold:
        cursorNew.execute(
            """select count(*) from public.app_iqprogram where program_id={} group by user_id""".format(
                prgmid,
                )
            )
        userCounts = [x[0] for x in cursorNew.fetchall()]
        
        # Since this is only users in the iqprogram table, each count should
        # be one
        assert len(userCounts) == sum(userCounts)    
        
    print("Income values updated")

    cursorNew.close()
    
def update_program_records(global_objects: dict) -> None:
    """
    The function modifies some records to account for missing logic in the v1
    app that had to be included in the extracts. The v2 app includes all logic
    related to program eligibility, so the extract will no longer account for
    these cases; this function modifies applicable records (created with the
    v1 app) so that the v2 extract doesn't have to account for them.
    
    For example, the v1 extract included logic to ensure an applicant's address
    was in the GMA; since v2 handles this in the app, the extract no longer
    needs that logic (and records prior to v2 need to be updated to match v2
    logic).
    
    Remove these iqprogram records here.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Beginning update IQ program application records...")
    warnings.warn("WARNING: there is no verification for this section")
    
    cursorNew = global_objects['conn_new'].cursor()
    
    # Find the app_iqprogram record IDs to delete
    cursorNew.execute(
        """select i.id from public.app_address a
        inner join public.app_addressrd r on a.eligibility_address_id=r.id
        right join (select ii.user_id, ii.id, ir.req_is_in_gma, ir.req_is_city_covered from public.app_iqprogram ii 
                    inner join public.app_iqprogramrd ir on ir.id=ii.program_id) i on i.user_id=a.user_id
        where (i.req_is_in_gma=true and r.is_in_gma=false) or (i.req_is_city_covered=true and r.is_city_covered=false)"""
        )
    deleteIqProgramIds = [x[0] for x in cursorNew.fetchall()]
    
    # Delete the found records
    cursorNew.execute(
        """delete from public.app_iqprogram where id in ({})""".format(
            ', '.join([str(x) for x in deleteIqProgramIds]),
            )
        )
    global_objects['conn_new'].commit()
    
    cursorNew.close()
    
    print("Program records updated")
        
if __name__=='__main__':
    
    # Define the generic profile ('_old' will be appended to this for the v1
    # connection)
    profile = input('Enter a generic database profile to use for porting: ')        