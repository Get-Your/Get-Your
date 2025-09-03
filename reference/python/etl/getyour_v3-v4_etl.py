"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Dec 26 12:48:07 2023

@author: TiCampbell

This script runs ETL on the v3.0 Get Your data to transform it for the v4
model.

"""

import coftc_cred_man as crd
import psycopg2
from rich import print
from rich.progress import Progress

# Define each renewal period. Per the specification, a NULL value for
# renewal_interval_year denotes a non-expiring program (e.g. lifetime
# enrollment)
RENEWAL_UPDATE_DICT = {
    "grocery": 1,
    "recreation": 1,
    "spin": None,
    "spin_community_pass": None,
    "connexion": None,
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
        (user_id,),
    )
    if cursor.fetchone()[0] == 0:
        return "app:address"

    # Check for record in app_household
    cursor.execute(
        """select count(*) from public.app_household where user_id=%s""",
        (user_id,),
    )
    if cursor.fetchone()[0] == 0:
        return "app:household"

    # Check for record in app_householdmembers
    cursor.execute(
        """select count(*) from public.app_householdmembers where user_id=%s""",
        (user_id,),
    )
    if cursor.fetchone()[0] == 0:
        return "app:household_members"

    # Check to see if the user has selected any eligibility programs
    cursor.execute(
        """select count(*) from public.app_eligibilityprogram where user_id=%s""",
        (user_id,),
    )
    programCount = cursor.fetchone()[0]
    if programCount == 0:
        return "app:programs"

    # Check to see if the user has uploaded all files
    # Django convention is to use 'blank' rather than 'null' for varchar
    # fields; check for both here, for completeness
    cursor.execute(
        """select count(*) from public.app_eligibilityprogram where user_id=%s and document_path is not null and document_path != ''""",
        (user_id,),
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
        fill_last_completed(global_objects)
        fill_last_notification(global_objects)
        add_renewal_interval_year(global_objects)

        verify_transfer(global_objects)

    except:
        raise

    else:
        print("[bright_cyan]Data update complete!")

    finally:
        global_objects["conn"].close()


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
    cred = crd.Cred(f"{profile}")

    conn = psycopg2.connect(
        "host={hst} user={usr} dbname={dbn} password={psw} sslmode={ssm}".format(
            hst=cred.config["host"],
            usr=cred.config["user"],
            dbn=cred.config["db"],
            psw=cred.password(),
            ssm="require",
        )
    )

    return {
        "conn": conn,
        "cred": cred,
    }


def fill_last_completed(global_objects: dict) -> None:
    """
    1) Fill all ``last_completed_at`` values.

    v4 is expanding the ``last_completed_at`` use case from the last renewal
    (this field was renamed from ``last_renewed_at``) to the last time the
    application portion was completed, so there can be no NULL values once a
    user sees the dashboard.

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

    cursor = global_objects["conn"].cursor()

    # Gather each user ID
    cursor.execute("""select "id" from public.app_user order by "id" """)
    userIds = [x[0] for x in cursor.fetchall()]

    # Loop through each user to get their current state
    try:
        with Progress() as progress:
            updateTask = progress.add_task(
                "[bright_cyan]Filling last_completed_at values",
                total=len(userIds),
            )

            for usrid in userIds:
                # Check if the user is redirected to the dashboard. If False,
                # last_completed_at should stay NULL (and are thus ignored here)
                if what_page_clone(cursor, usrid) == "app:dashboard":
                    # Check for NULL last_completed_at value
                    cursor.execute(
                        """select count(*) from public.app_user where id=%s and last_completed_at is null""",
                        (usrid,),
                    )
                    if cursor.fetchone()[0] != 0:
                        # Fill last_completed_at with max(modified_at) from
                        # app_eligibilityprogram (as a good approximation)
                        cursor.execute(
                            """select max(modified_at) from public.app_eligibilityprogram where user_id=%s""",
                            (usrid,),
                        )
                        returnedTimestamp = cursor.fetchone()[
                            0
                        ]  # there should always be a value

                        cursor.execute(
                            """update public.app_user set "last_completed_at"=%s where "id"=%s""",
                            (returnedTimestamp, usrid),
                        )

                progress.update(updateTask, advance=1)

        # Users that are mid-renewal will not be recognized correctly by
        # what_page[_clone](); override each last_completed at for
        # these users. Use each user's program they first applied to as the
        # date they last completed their application.

        # The override (instead of ignoring non-null) is because some of the
        # older accounts don't have a filled last_completed_at, even though
        # they obviously should
        cursor.execute(
            """update public.app_user u
            	set last_completed_at=i.first_applied_at
            	from (select user_id, min(applied_at) as first_applied_at from public.app_iqprogram group by user_id) as i
            	where u.id=i.user_id and u.is_archived = false and u.last_renewal_action is not null"""
        )

    except:
        global_objects["conn"].rollback()
        raise

    else:
        # Commit any changes after the loop runs
        global_objects["conn"].commit()

        print("last_completed_at fill complete!")

    finally:
        cursor.close()

    # Once last_completed_at is filled and mid-renewals addressed, pause to
    # manually correct some (older) last_renewal_action that are "stuck" at
    # an incomplete state before continuing to the last_action_notification_at
    # fill
    input(
        "\nPause here to manually revisit last_renewal_action values for users that are mid-renewal at this point. Follow instructions in the v4_cleanup_verification.sql script.\n\nPress Return to continue with the ETL script."
    )


def fill_last_notification(global_objects: dict) -> None:
    """
    2) Fill all ``last_action_notification_at`` values.

    ``last_action_notification_at`` (a new field) will henceforth be set as
    "action notifications" are being sent to users. Set all values to
    last_action_notification_at = last_completed_at.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.

    """

    cursor = global_objects["conn"].cursor()

    # Gather each user ID
    cursor.execute("""select "id" from public.app_user order by "id" """)
    userIds = [x[0] for x in cursor.fetchall()]

    # Loop through each user
    try:
        with Progress() as progress:
            updateTask = progress.add_task(
                "[bright_cyan]Filling last_action_notification_at values",
                total=len(userIds),
            )

            # Set all last_action_notification_at to last_completed_at in SQL
            cursor.execute(
                """update public.app_user set last_action_notification_at=last_completed_at where last_completed_at is not null;"""
            )

            progress.update(updateTask, advance=1)

    except:
        global_objects["conn"].rollback()
        raise

    else:
        # Commit any changes after the loop runs
        global_objects["conn"].commit()

        print("last_action_notification_at fill complete!")

    finally:
        cursor.close()


def add_renewal_interval_year(global_objects: dict) -> None:
    """
    3) Fill ``renewal_interval_year`` for all IQ Programs. This is the number
    of years between each necessary renewal.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.

    """

    cursor = global_objects["conn"].cursor()

    # Since the update allows NULLs, validation will be done within this function

    # Ensure all programs are accounted for in RENEWAL_UPDATE_DICT
    cursor.execute(
        """select "program_name" from public.app_iqprogramrd order by "program_name" """
    )
    dbNames = [x[0] for x in cursor.fetchall()]
    assert dbNames == sorted(RENEWAL_UPDATE_DICT.keys())

    # Loop through each program and update renewal_interval_year
    try:
        with Progress() as progress:
            updateTask = progress.add_task(
                "[bright_cyan]Updating Renewal Interval value",
                total=len(RENEWAL_UPDATE_DICT.keys()),
            )

            for prg in RENEWAL_UPDATE_DICT.keys():
                cursor.execute(
                    """update public.app_iqprogramrd set "renewal_interval_year"=%s where "program_name"=%s""",
                    (RENEWAL_UPDATE_DICT[prg], prg),
                )

            progress.update(updateTask, advance=1)

    except:
        global_objects["conn"].rollback()
        raise

    else:
        # Commit any changes after the loop runs
        global_objects["conn"].commit()

        print("renewal_interval_year fill complete!")

    finally:
        cursor.close()


def verify_transfer(global_objects: dict) -> None:
    """
    Verify the proper transfer of all data.

    Ensure
    1) all non-NULL last_completed_at values represent users who have reached
    the dashboard OR have a non-null last_renewal_action, and
    last_action_notification_at == last_completed_at
    2) all NULL last_completed_at values represent users who have *not* reached
    the dashboard, and last_action_notification_at == last_completed_at
    3) all programs in RENEWAL_UPDATE_DICT have been
    correctly added to app_iqprogramrd.

    Parameters
    ----------
    global_objects : dict
        Dictionary of objects used across all functions.

    Returns
    -------
    None.

    """

    cursor = global_objects["conn"].cursor()

    try:
        # First: verify all non-NULL last_completed_at values
        cursor.execute(
            """select "id", "last_completed_at", "last_action_notification_at" from public.app_user where "last_completed_at" is not null"""
        )
        nonNullUserTs = cursor.fetchall()

        with Progress() as progress:
            verifyTask = progress.add_task(
                "[bright_cyan]Verifying non-NULL last_completed_at",
                total=len(nonNullUserTs),
            )

            for usrid, completeat, notifyat in nonNullUserTs:
                # Either what_page_clone() puts the user at the dashboard or
                # last_renewal_action is non-null. completeat == notifyat for
                # either case
                try:
                    assert (
                        what_page_clone(cursor, usrid) == "app:dashboard"
                        and completeat == notifyat
                    )
                except AssertionError:
                    cursor.execute(
                        "select count(*) from public.app_user where id=%s and last_renewal_action is not null",
                        (usrid,),
                    )
                    assert cursor.fetchone()[0] > 0 and completeat == notifyat
                progress.update(verifyTask, advance=1)

        # Second: verify all NULL last_completed_at values
        cursor.execute(
            """select "id", "last_completed_at", "last_action_notification_at" from public.app_user where "last_completed_at" is null"""
        )
        nullUserTs = cursor.fetchall()

        with Progress() as progress:
            verifyTask = progress.add_task(
                "[bright_cyan]Verifying NULL last_completed_at",
                total=len(nullUserTs),
            )

            for usrid, completeat, notifyat in nullUserTs:
                assert (
                    what_page_clone(cursor, usrid) != "app:dashboard"
                    and notifyat is None
                )
                progress.update(verifyTask, advance=1)

        # Third: verify correct update of IQ Program renewal intervals
        with Progress() as progress:
            verifyTask = progress.add_task(
                "[bright_cyan]Verifying Renewal Interval values",
                total=len(RENEWAL_UPDATE_DICT.keys()),
            )

            for prg, mos in RENEWAL_UPDATE_DICT.items():
                cursor.execute(
                    """select "renewal_interval_year" from public.app_iqprogramrd where "program_name"=%s""",
                    (prg,),
                )
                assert cursor.fetchone()[0] == mos
                progress.update(verifyTask, advance=1)

    except:
        global_objects["conn"].rollback()
        raise

    else:
        print("All porting verified!")

    finally:
        cursor.close()


if __name__ == "__main__":
    # Define the database profile
    profile = input("Enter the database profile to use for porting: ")

    print(
        "\nETL script initialized. To continue, execute\n\nrun_full_porting(profile)\n"
    )
