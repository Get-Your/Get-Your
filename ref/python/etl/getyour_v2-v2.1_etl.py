# -*- coding: utf-8 -*-
"""
Created on Fri May 12 08:48:56 2023

@author: TiCampbell

This script runs ETL on the v2 Get Your data to transform it for the v2.1
model.

The only change that needs to be made for this version update is to copy the
'identification' file path from app_eligibilityprogram to the JSON object in
app_householdmembers.

"""

from rich import print
from rich.progress import Progress
import psycopg2
import json

import coftc_cred_man as crd

def run_full_porting(profile):
    """
    Run all ETL, in order.

    Returns
    -------
    None.

    """
    
    print(
        "[bright_cyan]Updating '{}' database...".format(
            profile,
            )
        )

    global_objects = initialize_vars(profile)

    port_identification_path_reference(global_objects)
    deactivate_identification_program(global_objects)
    
    verify_transfer(global_objects)
    
    global_objects['conn'].close()
    
    print('[bright_cyan]Transfer of the data complete!')

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
    
    # Connect to the database
    cred = crd.Cred(f'{profile}')

    conn = psycopg2.connect(
        "host={hst} user={usr} dbname={dbn} password={psw} sslmode={ssm}".format(
            hst=cred.config['host'],
            usr=cred.config['user'],
            dbn=cred.config['db'],
            psw=cred.password(),
            ssm='require')
        ) 
    
    return(
        {
            'conn': conn,
            'cred': cred,
            }
        )

def port_identification_path_reference(global_objects: dict) -> None:
    """
    1) Add a ``null`` value to ``identification_path`` for the relevant section
    in the JSON object in app_householdmembers if 'identification' in the
    app_eligibilityprogram table exists for the user. See 
    https://github.com/Get-Your/Get-Your/issues/249 for reference.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    # Gather program_id for the 'identification' "program"
    cursor.execute("""select "id" from public.app_eligibilityprogramrd where "program_name"='identification'""")
    programId = cursor.fetchone()[0]
    
    # Gather all users and filepaths in the eligibilityprogram table with a
    # non-null and non-blank identification document_path
    cursor.execute(
        """select "user_id", "document_path" from public.app_eligibilityprogram where "program_id"={} and "document_path" is not null and "document_path"!=''""".format(
            programId,
            )
        )
    userPaths = cursor.fetchall()
    
    with Progress() as progress:

        updateTask = progress.add_task(
            "[bright_cyan]Updating identification_path values",
            total=len(userPaths),
            )

        # Loop through each user
        for userid, _ in userPaths:
    
            # Gather the householdmembers JSON object
            cursor.execute(
                """select "household_info" from public.app_householdmembers where user_id={}""".format(
                    userid,
                    )
                )
            dbOut = cursor.fetchone()
            
            if dbOut is not None:
                memberDict = dbOut[0]
            
                # Add 'identification_path' key (with value ``null``) to each list
                # item where it doesn't already exist
                isUpdated = False   # initialize whether to run update
                for jsonidx,jsonitm in enumerate(memberDict['persons_in_household']):
                    # Only update if the key doesn't already exist
                    if 'identification_path' not in jsonitm.keys():
                        
                        # Add the key with a null value
                        memberDict['persons_in_household'][jsonidx]['identification_path'] = None
                        
                        # Ensure isUpdated is set (each loop is just redundant)
                        isUpdated = True
                    
                # Update the record with the new JSON object, if applicable
                if isUpdated:
                    cursor.execute(
                        """update public.app_householdmembers set "household_info"=%s where "user_id"={}""".format(
                            userid,
                            ),
                        (json.dumps(memberDict), )
                        )
                    
            progress.update(updateTask, advance=1)
        
    # Commit any changes
    global_objects['conn'].commit()
    
    print('identification_path reference port complete!')
    
    cursor.close()
    
def deactivate_identification_program(global_objects: dict) -> None:
    """
    2) Deactivate the 'identification' "program" in the
    app_eligibilityprogramrd table.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    cursor.execute(
        """update public.app_eligibilityprogramrd set "is_active"=false where "program_name"='identification'"""
        )
    
    global_objects['conn'].commit()

def verify_transfer(global_objects: dict) -> None:
    """
    Verify the proper transfer of all data.
    
    Ensure all newly-written identification_path records (with null values)
    have a matching 'identification' record.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    # Go through each user with a null identification_path and verify they
    # have a matching 'identification' record in app_eligibilityprogram
    
    cursor = global_objects['conn'].cursor()
    
    # Gather program_id for the 'identification' "program"
    cursor.execute("""select "id" from public.app_eligibilityprogramrd where "program_name"='identification'""")
    programId = cursor.fetchone()[0]
    
    # Gather all users and filepaths in the eligibilityprogram table with a
    # non-null and non-blank identification document_path
    cursor.execute(
        """select "user_id" from public.app_householdmembers where "household_info" is not null"""
        )
    userList = [x[0] for x in cursor.fetchall()]
    
    # Loop through each user
    for userid in userList:

        # Gather the householdmembers JSON object
        cursor.execute(
            """select "household_info" from public.app_householdmembers where user_id={}""".format(
                userid,
                )
            )
        dbOut = cursor.fetchone()
        
        if dbOut is not None:
            memberDict = dbOut[0]
        
            for jsonidx,jsonitm in enumerate(memberDict['persons_in_household']):
                # Check for null value for each 'identification_path'
                if 'identification_path' in jsonitm.keys() and jsonitm['identification_path'] is None:
                    
                    # Verify there is at least one filled 'identification'
                    # record in app_eligibilityprogram for this user
                    cursor.execute(
                        """select count(*) from public.app_eligibilityprogram where "user_id"={} and "program_id"={} and "document_path" is not null and "document_path"!=''""".format(
                        userid,
                        programId,
                        )
                    )
                    recordCount = cursor.fetchone()[0]
                    
                    if recordCount < 1:
                        raise AssertionError(
                            f"User {userid} does not have an 'identification' record"
                            )
    
    cursor.close()    
    
        
if __name__=='__main__':
    
    # Define the database profile
    profile = input('Enter the database profile to use for porting: ')        