# -*- coding: utf-8 -*-
"""
Created on Tue Dec 26 12:48:07 2023

@author: TiCampbell

This script runs ETL on the v3.0 Get Your data to transform it for the v4
model.

"""

from rich import print
from rich.progress import Progress
import psycopg2
import json

import coftc_cred_man as crd


## Initialize vars
    
# Define the ordered list of pages that will be used for the values in
# `last_application_action`. This is directly from app.constant
APPLICATION_PAGES = {
    'get_ready': 'app:get_ready',
    'account': 'app:account',
    'address': 'app:address',
    'household': 'app:household',
    'household_members': 'app:household_members',
    'eligibility_programs': 'app:programs',
    'files': 'app:files'
}


def what_page_clone(
        cursor: psycopg2.extensions.cursor,
        user_id: int,
    ) -> str:
    """
    Clone of what_page(), adjusted for bare database calls.

    Parameters
    ----------
    cursor : psycopg2.extensions.cursor
        Database cursor to use for the queries.
    user_id : int
        ID of the user in question.

    Returns
    -------
    str
        Returns the target page designation.

    """

    # Check for record in app_address
    cursor.execute(
        """select count(*) from public.app_address where user_id=%s""",
        (user_id, ),
    )
    if cursor.fetchone()[0] == 0:
        return "app:address"
    
    # Check for record in app_household
    cursor.execute(
        """select count(*) from public.app_household where user_id=%s""",
        (user_id, ),
    )
    if cursor.fetchone()[0] == 0:
        return "app:household"

    # Check for record in app_householdmembers
    cursor.execute(
        """select count(*) from public.app_householdmembers where user_id=%s""",
        (user_id, ),
    )
    if cursor.fetchone()[0] == 0:
        return "app:household_members"

    # Check to see if the user has selected any eligibility programs
    cursor.execute(
        """select count(*) from public.app_eligibilityprogram where user_id=%s""",
        (user_id, ),
    )
    programCount = cursor.fetchone()[0]
    if programCount == 0:
        return "app:programs"
    
    # Check to see if the user has uploaded all files
    # Django convention is to use 'blank' rather than 'null' for varchar
    # fields; check for both here, for completeness
    cursor.execute(
        """select count(*) from public.app_eligibilityprogram where user_id=%s and document_path is not null and document_path != ''""",
        (user_id, ),
    )
    fileCount = cursor.fetchone()[0]
    if fileCount < programCount:
        return "app:files"

    # If all checks pass, return 'dashboard'
    return "app:dashboard"


def what_page_application(last_application_action):
    """
    The new what_page_application flow.

    Returns:
        str: The target page for the initial application flow
    """

    for page, url in APPLICATION_PAGES.items():
        if page not in last_application_action:
            return url

    # Default return if all pages are present
    return 'app:dashboard'


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

    try:
        fill_last_application_action(global_objects)
        
        verify_transfer(global_objects)
        
    except:
        raise
        
    else:
        print('[bright_cyan]Data update complete!')
        
    finally:
        global_objects['conn'].close()


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


def fill_last_application_action(global_objects: dict) -> None:
    """
    1) Fill all values for the new field ``last_application_action``.
    
    If ``last_completed_at`` is None and what_page() returns 'app:dashboard',
    set last_completed_at = max(app_eligibilityprogram.modified_at).

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    # Gather each user ID where the user isn't in the middle of a renewal (if
    # they're in a renewal, what_page_clone() wouldn't recognize them properly;
    # but more pertinently, their last_application_action should remain NULL)
    cursor.execute("""select "id" from public.app_user where "last_renewal_action" is null order by "id" """)
    userIds = [x[0] for x in cursor.fetchall()]

    # Loop through each user to get their current state
    try:
        with Progress() as progress:

            updateTask = progress.add_task(
                "[bright_cyan]Filling last_application_action values",
                total=len(userIds),
            )
            
            for usrid in userIds:
                
                # Check if the user is redirected to the dashboard. If False,
                # last_application_action should stay NULL
                whatPage = what_page_clone(cursor, usrid)
                if whatPage != 'app:dashboard':
                    
                    # The following is taken from app.backend.save_user_action()
                    
                    # Initialize dict for the ETL script
                    last_application_action = {}

                    # Find the pages the user had progressed through
                    completedPages = []
                    for nm, pg in APPLICATION_PAGES.items():
                        if pg == whatPage:
                            break
                        completedPages.append(nm)
                        
                    # Build the JSON as if the user had gone through the pages
                    for nm in completedPages:
                        last_application_action[nm] = {'data': {}, 'status': 'completed'}

                    cursor.execute(
                        """update public.app_user set "last_application_action"=%s where "id"=%s""",
                        (json.dumps(last_application_action), usrid),
                    )
                    
                progress.update(updateTask, advance=1)
       
    except:
        global_objects['conn'].rollback()
        raise
        
    else:
        # Commit any changes after the loop runs
        global_objects['conn'].commit()
    
        print('last_completed_at fill complete!')
        
    finally:
        cursor.close()


def verify_transfer(global_objects: dict) -> None:
    """
    Verify the proper transfer of all data.
    
    Ensure
    1) last_application_action is null if last_renewal_action is not null
    2) all last_application_action values with null last_renewal_action have
    the proper what_page_clone() output
    3) all users with has_viewed_dashboard==True have a NULL
    last_application_action

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    try:
        # First: verify all last_application_action is NULL if
        # last_renewal_action is not NULL
        cursor.execute(
            """select count(*) from public.app_user where "last_renewal_action" is not null and "last_application_action" is not null"""
        )
        assert cursor.fetchone()[0] == 0
        
        # Second: verify all last_application_action values when
        # last_renewal_action is NULL
        cursor.execute(
            """select "id", "last_application_action" from public.app_user where "last_renewal_action" is null"""
        )
        userAction = cursor.fetchall()
        
        with Progress() as progress:

            verifyTask = progress.add_task(
                "[bright_cyan]Verifying last_application_action values",
                total=len(userAction),
            )
        
            for usrid, action in userAction:
                # Assert that the old what_page() gives the same result as the
                # new what_page_application()
                whatPage = what_page_clone(cursor, usrid)
                assert whatPage == 'app:dashboard' or whatPage == what_page_application(action)

                progress.update(verifyTask, advance=1)

    except:
        raise
        
    try:
        # Last: verify all users with has_viewed_dashboard also have a NULL
        # last_application_action
        cursor.execute(
            """select "id", "last_application_action" from public.app_user where "has_viewed_dashboard" is true"""
        )
        userActions = cursor.fetchall()
        
        assert all([x[1] is None for x in userActions])
        
    except:
        raise
        
    else:
        print('All porting verified!')
        
    finally:
        cursor.close()

        
if __name__=='__main__':
    
    # Define the database profile
    profile = input('Enter the database profile to use for porting: ')
    
    print(
        "\nETL script initialized. To continue, execute\n\nrun_full_porting(profile)\n"
    )