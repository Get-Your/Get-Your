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
import psycopg2
import json
import warnings
import ast

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

    port_identification_path(global_objects)
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
    
def port_identification_path(global_objects: dict) -> None:
    """
    1) Copy 'identification' from the app_eligibilityprogram table to the
    relevant section in the JSON object in app_householdmembers.

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
    # non-null identification document_path
    cursor.execute(
        """select "user_id", "document_path" from public.app_eligibilityprogram where "program_id"={} and "document_path" is not null""".format(
            programId,
            )
        )
    userPaths = cursor.fetchall()
    
    # Loop through each user
    warnings.warn('WARNING: literal_eval() is potentially dangerous. Best to find a different solution to storing multiple files.')
    for userid, pathitm in userPaths:

        # Gather the lowercase first and last name for the user to combine and
        # compare to each element of the JSON object
        cursor.execute(
            """select "first_name", "last_name" from public.app_user where id={}""".format(
                userid,
                )
            )
        nameList = [x.lower() for x in cursor.fetchone()]
        
        # Gather the householdmembers JSON object
        cursor.execute(
            """select "household_info" from public.app_householdmembers where user_id={}""".format(
                userid,
                )
            )
        memberDict = cursor.fetchone()[0]
        
        # If the user's first/last name matches any element in the JSON object,
        # set the identification_path to the delistified pathitm
        isUpdated = False   # initialize whether to run update
        for jsonidx,jsonitm in enumerate(memberDict['persons_in_household']):
            # Compare each jsonitm name with app_user name (case-insensitive)
            if jsonitm['name'].lower() == ' '.join(nameList):
                
                # Convert the path(s) to a Python list
                pathitm = ast.literal_eval(pathitm)
                
                # Insert the first value of pathitm into a new
                # 'identification_path' key
                if len(pathitm) > 1:
                    print(f"WARNING: document_path for user {userid} is more than 1 file; truncated")
                
                memberDict['persons_in_household'][jsonidx]['identification_path'] = pathitm[0]
                
                # Stop after the first match
                isUpdated = True
                break
            
        # Update the record with the new JSON object, if applicable
        if isUpdated:
            cursor.execute(
                """update public.app_householdmembers set "household_info"=%s where "user_id"={}""".format(
                    userid,
                    ),
                (json.dumps(memberDict), )
                )
        
    # Commit any changes
    global_objects['conn'].commit()
    
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

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    print("Since this is non-critical (more of a convenience), there is no verification for this ETL")
        
if __name__=='__main__':
    
    # Define the generic profile ('_old' will be appended to this for the v1
    # connection)
    profile = input('Enter a generic database profile to use for porting: ')        