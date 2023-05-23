# -*- coding: utf-8 -*-
"""
Created on Fri May 12 08:48:56 2023

@author: TiCampbell

This script runs ETL on the v1 Get FoCo data to transform and port it to the
v2 Get Your database.

"""

from typer import prompt
from rich import print
import psycopg2
import hashlib
import json

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
    
    currentUserAddition = 100000
    update_current_users(global_objects)
    port_user(global_objects)
    port_address(global_objects)
    port_eligibility(global_objects)
    # Note that there is no corresponding eligibility history in PROD or STAGE
    port_householdmembers(global_objects)
    port_iqprograms(global_objects)
    port_eligibility_programs(global_objects)
    
    print('[bright_cyan]PSC update from JDE complete!')

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
    
    return(
        {
            'conn_new': connNew,
            'conn_old': connOld,
            'cred_new': credNew,
            'cred_old': credOld,
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
    cursorNew.execute("update public.app_address set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_household set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_householdmembers set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_householdhist set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_iqprogram set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_eligibilityprogram set user_id=user_id+{cradd} where user_id<{cradd}".format(cradd=currentUserAddition))
    cursorNew.execute("update public.app_user set id=id+{cradd} where id<{cradd}".format(cradd=currentUserAddition))
    
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
    
    cursorOld.execute("""SELECT "id", "password", "last_login", "is_superuser", "is_staff", "is_active", "date_joined", "email", "first_name", "last_name", "phone_number", "has_viewed_dashboard", "is_archived"
                      from public.application_user""")
    userList = cursorOld.fetchall()
    
    if len(userList) > 0:
        cursorNew.execute("""insert into public.app_user ("id", "password", "last_login", "is_superuser", "is_staff", "is_active", "date_joined", "email", "first_name", "last_name", "phone_number", "has_viewed_dashboard", "is_archived")
                          VALUES {}""".format(
                ', '.join(['%s']*len(userList))
                ),
            userList,
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
            
            cursorNew.execute("""INSERT INTO public.app_address ("created_at", "modified_at", "user_id", "eligibility_address_id", "mailing_address_id")
                              VALUES ({})""".format(
                              ', '.join(['%s']*(len(usrFields)+2))
                              ),
                        list(usritm[-len(usrFields):])+[idVal, idVal],
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
    

    cursorOld.execute("""SELECT "created", "modified", "user_id_id", False, (CASE WHEN "rent" NOT IN ('Rent', 'Own') THEN "rent" ELSE '' END), "dependents", "AmiRange_min", "AmiRange_max", (CASE WHEN "GenericQualified"='ACTIVE' THEN true ELSE false END), (CASE WHEN "rent" IN ('Rent', 'Own') THEN LOWER("rent") ELSE '' END) FROM public.application_eligibility""")
    eligList = cursorOld.fetchall()
    
    if len(eligList) > 0:
        cursorNew.execute("""insert into public.app_household ("created_at", "modified_at", "user_id", "is_updated", "duration_at_address", "number_persons_in_household", "ami_range_min", "ami_range_max", "is_income_verified", "rent_own")
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
          """Run the ETL from MoreInfo via Django with the following:
    1) Switch to branch ``database-rearchitecture-p0-modifytable`` in the GetFoco repo
    2) Run the GetFoco app using ``settings.local_<target_database>db`` (you may need to ``makemigrations``/``migrate`` first)
    3) Navigate to 127.0.0.1:8000/application/rearch_phase0 to write to public.application_moreinfo_rearch in the GetFoco database.
    Continue this script to finish porting to GetYour."""
    )
    
    # modified_at is written automatically, so now we need to overwrite it from the temporary fields
    cursorOld.execute(
        """update public.application_moreinfo_rearch set "created_at"="created_at_init_temp", "modified_at"="modified_at_init_temp" """
        )
    global_objects['conn_old'].commit()
    
    # Move public.application_moreinfo_rearch to public.app_householdmembers
    # (directly, except for init_temp fields - ignore these completely)
    cursorOld.execute("""SELECT "created_at", "modified_at", "user_id", "household_info" FROM public.application_moreinfo_rearch""")
    membersList = cursorOld.fetchall()
    
    if len(membersList) > 0:
        cursorNew.execute("""insert into public.app_householdmembers ("created_at", "modified_at", "user_id", "household_info")
                          VALUES {}""".format(
                ', '.join(['%s']*len(membersList))
                ),
            # Serialize the JSON in membersList
            [tuple([json.dumps(y) if idx==len(x)-1 else y for idx,y in enumerate(x)]) for x in membersList],
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
        
        ## TODO: Port getfoco_dev.public.application_iqprogramqualifications_rearch
        ## to public.app_iqprogramrd in *all environments*
        
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

        
if __name__=='__main__':
    
    # Define the generic profile ('_old' will be appended to this for the v1
    # connection)
    genericProfile = prompt('Enter a generic database profile to use for porting')        