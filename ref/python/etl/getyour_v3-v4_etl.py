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
    cursor.execute(
        """select count(*) from public.app_eligibilityprogram where user_id=%s and document_path is not null""",
        (user_id, ),
    )
    fileCount = cursor.fetchone()[0]
    if fileCount < programCount:
        return "app:files"

    # If all checks pass, return 'dashboard'
    return "app:dashboard"


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
        filledIds = fill_last_completed_and_notification(global_objects)
        add_renewal_interval_month(global_objects)
        
        verify_transfer(global_objects, filledIds)
        
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


def fill_last_completed_and_notification(global_objects: dict) -> None:
    """
    1) Fill all ``last_completed_at`` and ``last_action_notification_at``
    values.
    
    v4 is expanding the ``last_completed_at`` use case from the last renewal
    (this field was renamed from ``last_renewed_at``) to the last time the
    application portion was completed, so there can be no NULL values once a
    user sees the dashboard.
    
    If ``last_completed_at`` is None and what_page() returns 'app:dashboard',
    set last_completed_at = last_action_notification_at =
    max(app_eligibilityprogram.modified_at).
    
    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    # Gather each user ID
    cursor.execute("""select "id" from public.app_user order by "id" """)
    userIds = [x[0] for x in cursor.fetchall()]

    # Loop through each user
    idsToFill = []      # initialize for use in validation
    try:
        for usrid in userIds:
    
            # Check for NULL last_completed_at value
            cursor.execute(
                """select count(*) from public.app_user where id=%s and last_completed_at is null""",
                (usrid, ),
            )
            if cursor.fetchone()[0] != 0:
                # last_completed_at is NULL; check if user is redirected to dashboard
                if what_page_clone(cursor, usrid) == 'app:dashboard':
                    # Fill last_completed_at and last_action_notification_at
                    # with max(modified_at) from app_eligibilityprogram (as a
                    # good approximation)
                    cursor.execute(
                        """select max(modified_at) from public.app_eligibilityprogram where user_id=%s""",
                        (usrid, ),
                    )
                    returnedTimestamp = cursor.fetchone()[0]     # there should always be a value
                    
                    cursor.execute(
                        """update public.app_user set "last_completed_at"=%s, "last_action_notification_at"=%s where "id"=%s""",
                        (returnedTimestamp, returnedTimestamp, usrid),
                    )
                    
                    idsToFill.append(usrid)
                    
    except:
        global_objects['conn'].rollback()
        raise
        
    else:
        # Commit any changes after the loop runs
        global_objects['conn'].commit()
    
        print('last_completed_at fill complete!')
        
    finally:
        cursor.close()


def add_renewal_interval_month(global_objects: dict) -> None:
    """
    2) Fill ``renewal_interval_month`` for all IQ Programs. This is the number
    of months between each necessary renewal.
    
    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    # Define each renewal period. Per the specification, a NULL value for
    # renewal_interval_month denotes a non-expiring program (e.g. lifetime
    # enrollment)
    updateDict = {
        'grocery': 12,
        'recreation': 12,
        'spin': None,
        'spin_community_pass': None,
        'connexion': None,
    }
    
    # Since the update allows NULLs, validation will be done within this function
    
    # Ensure all programs are accounted for in updateDict
    cursor.execute("""select "program_name" from public.app_iqprogramrd order by "program_name" """)
    dbNames = [x[0] for x in cursor.fetchall()]
    assert dbNames == sorted(updateDict.keys())

    # Loop through each program and update renewal_interval_month
    try:
        for prg in updateDict.keys():
            cursor.execute(
                """update public.app_iqprogramrd set "renewal_interval_month"=%s where "program_name"=%s""",
                (updateDict[prg], prg),
            )
                    
    except:
        global_objects['conn'].rollback()
        raise
        
    else:
        # Commit any changes after the loop runs
        global_objects['conn'].commit()
    
        print('renewal_interval_month fill complete!')
        
    finally:
        cursor.close()


def verify_transfer(global_objects: dict, filled_ids: list) -> None:
    """
    Verify the proper transfer of all data.
    
    Ensure all newly-written identification_path records (with null values)
    have a matching 'identification' record.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.
    filled_ids : list
        List of User IDs that were marked to be filled in fill_last_completed_and_notification.

    Returns
    -------
    None.
    
    """
    
    cursor = global_objects['conn'].cursor()
    
    try:
        # First: verify that all users with a non-null last_completed_at have
        # the same value for last_action_notification_at
        cursor.execute(
            """select last_completed_at=last_action_notification_at from public.app_user where last_completed_at is not null"""
        )
        assert all([x[0] for x in cursor.fetchall()])
        
        # Now we can assume last_action_notification_at is correct and only
        # use last_completed_at
        # Verify that all users in filled_ids have a last_completed_at value
        cursor.execute(
            """select count(*) from public.app_user where last_completed_at is not null and id in ({})""".format(
                ','.join(['%s']*len(filled_ids))
            ),
            filled_ids,
        )
        assert len(filled_ids) == cursor.fetchone()[0]
    
        # Verify all users that have non-null last_completed_at have reached
        # the dashboard
        cursor.execute("""select "id" from public.app_user where last_completed_at is not null order by "id" """)
        nonNullIds = [x[0] for x in cursor.fetchall()]
    
        # Loop through each user
        for usrid in nonNullIds:
            if what_page_clone(cursor, usrid) != 'app:dashboard':
                # Raise exception if this user hasn't reached the dashboard
                raise TypeError(
                    f"User {usrid} has a non-null `last_completed_at` but hasn't reached the dashboard"
                )
                
        # Verify all users that have a *null* last_completed_at have *not*
        # reached the dashboard
        cursor.execute("""select "id" from public.app_user where last_completed_at is null order by "id" """)
        nullIds = [x[0] for x in cursor.fetchall()]
    
        # Loop through each user
        for usrid in nullIds:
            if what_page_clone(cursor, usrid) == 'app:dashboard':
                # Raise exception if this user has reached the dashboard
                raise TypeError(
                    f"User {usrid} has a null `last_completed_at` but has reached the dashboard (i.e. it should be filled)"
                )
                    
    except:
        global_objects['conn'].rollback()
        raise
        
    else:
        print('All porting verified!')
        
    finally:
        cursor.close()

        
if __name__=='__main__':
    
    # Define the database profile
    profile = input('Enter the database profile to use for porting: ')        