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