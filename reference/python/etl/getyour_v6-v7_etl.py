# -*- coding: utf-8 -*-
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

"""
This script runs ETL on the v6.0 Get-Your data to transform it for the v7
model.

"""

import re
import sys
from pathlib import Path
from typing import Union

import pandas as pd
from psycopg.errors import FeatureNotSupported
from sqlalchemy import (
    Column,
    Integer,
    Table,
    bindparam,
    cast,
    delete,
    func,
    literal_column,
    select,
    text,
    update,
)

# Use Postgres-specific insert
from sqlalchemy.dialects.postgresql import insert

# Add the path of this directory's parent, then import helper functions
sys.path.append(str(Path(__file__).parents[1]))
from helper_functions import (
    DBMetadata,
    FieldMapping,
    finalize_df_for_database,
    process_data,
    upsert_via_merge,
)

# Return the directory of this file
FILE_DIR = Path(__file__).parent

# Define the mapping from Postgres datatypes to Python. This is a regex from
# the Postgres dtypes
DTYPE_MAPPING = {
    "(.*?INT.*?)": "Int64",
    "(.*?TIMESTAMP.*?)": "str",
    "(.*?CHAR.*?)": "str",
    "(.*?TEXT.*?)": "str",
    "(.*?JSON.*?)": "str",
    "(BOOLEAN)": "bool",
    "(NUMERIC.*?)": "float",
}


class TableFunctions:
    def __init__(self, etl_object):
        """Table-specific functions for the ETL process."""
        self.etlo = etl_object

    def determine_completed_pages(self):
        """
        For each user, determine how to fill User.user_completed_pages.

        This will either be from the JSON in last_renewal_action or,
        secondarily, from the calculation in app.backend.what_page().

        """

        # Load the source and target tables from metadata reflections
        source_user_table = Table(
            "app_user",
            self.etlo.old.metadata,
            autoload_with=self.etlo.old.engine,
        )
        source_address_table = Table(
            "app_address",
            self.etlo.old.metadata,
            autoload_with=self.etlo.old.engine,
        )
        source_household_table = Table(
            "app_household",
            self.etlo.old.metadata,
            autoload_with=self.etlo.old.engine,
        )
        source_householdmembers_table = Table(
            "app_householdmembers",
            self.etlo.old.metadata,
            autoload_with=self.etlo.old.engine,
        )
        source_eligibilityprogram_table = Table(
            "app_eligibilityprogram",
            self.etlo.old.metadata,
            autoload_with=self.etlo.old.engine,
        )
        target_table = Table(
            "users_user_user_completed_pages",
            self.etlo.new.metadata,
            autoload_with=self.etlo.new.engine,
        )

        # This section is modified app.backend.what_page() (for use outside the
        # webapp)

        # See if user.address exists
        stmt = select(
            source_address_table.c.user_id,
        )
        with self.etlo.old.engine.begin() as conn:
            result = conn.execute(stmt)
            address_exists_dict = {rw.user_id: True for rw in result}

        # See if user.household exists
        stmt = select(
            source_household_table.c.user_id,
        )
        with self.etlo.old.engine.begin() as conn:
            result = conn.execute(stmt)
            household_exists_dict = {rw.user_id: True for rw in result}

        # See if HouseholdMembers has been filled
        stmt = select(
            source_householdmembers_table.c.user_id,
        )
        with self.etlo.old.engine.begin() as conn:
            result = conn.execute(stmt)
            householdmembers_exists_dict = {rw.user_id: True for rw in result}

        stmt = (
            select(
                source_eligibilityprogram_table.c.user_id,
                func.sum(
                    cast(source_eligibilityprogram_table.c.document_path == "", Integer)
                ).label("empty_uploads_count"),
            )
            .order_by(
                source_eligibilityprogram_table.c.user_id,
            )
            .group_by(source_eligibilityprogram_table.c.user_id)
        )
        with self.etlo.old.engine.begin() as conn:
            result = conn.execute(stmt)
            empty_uploads_dict = {rw.user_id: rw.empty_uploads_count for rw in result}

        # Define the mapping from 'page name' to ref.ApplicationPage.page_url
        # This is the `application_pages` var in the v6 app.constants
        application_page_mapping = {
            "get_ready": "app:get_ready",
            "account": "users:signup",
            "address": "app:address",
            "household": "app:household",
            "household_members": "app:household_members",
            "eligibility_programs": "app:programs",
            "files": "app:files",
        }

        # Gather the last_renewal_action field for all users
        stmt = select(
            source_user_table.c.id,
            source_user_table.c.last_renewal_action,
        ).order_by("id")
        with self.etlo.old.engine.begin() as conn:
            result = conn.execute(stmt)
            renewals_dict = {rw.id: rw.last_renewal_action for rw in result}

        # Loop through users to determine completed application pages in the v7
        # model

        # Initialize a list for insert
        complete_pages = []
        for user_id, renewal in renewals_dict.items():
            # Check the last_renewal_action dictionary first; this held
            # precedence in the v6 app
            if renewal is not None:
                # For each element with 'status: completed', find the page_url
                # using application_page_mapping and set that page as 'complete'
                # for the current user in the v7
                # 'users_user_user_completed_pages' table
                complete_pages.extend(
                    [
                        {
                            "user_id": user_id,
                            "page_url": application_page_mapping[ky],
                        }
                        for ky, vl in renewal.items()
                        if vl["status"] == "completed"
                    ]
                )

            else:
                # If no renewal exists, use v6 app.backend.what_page() to
                # determine what pages are complete

                # Initialize complete_pages with 'get_ready' and 'account'
                # (because the user exists)
                complete_pages.extend(
                    [
                        {"user_id": user_id, "page_url": "app:get_ready"},
                        {"user_id": user_id, "page_url": "users:signup"},
                    ]
                )

                if user_id in address_exists_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:address"},
                    )
                if user_id in household_exists_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:household"}
                    )
                if user_id in householdmembers_exists_dict:
                    complete_pages.append(
                        {
                            "user_id": user_id,
                            "page_url": "app:household_members",
                        }
                    )
                # Check to see if the user has selected any eligibility programs
                if user_id in empty_uploads_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:programs"}
                    )
                    # Check if any of the eligibility programs have empty uploads
                    if empty_uploads_dict[user_id] == 0:
                        complete_pages.append(
                            {"user_id": user_id, "page_url": "app:files"}
                        )

        # Convert insert list to DataFrame
        df_completed = pd.DataFrame(data=complete_pages)

        # Gather the ID for each applicationpage_url
        applicationpage_table = Table(
            "ref_applicationpage",
            self.etlo.new.metadata,
            autoload_with=self.etlo.new.engine,
        )
        stmt = select(applicationpage_table.c.id, applicationpage_table.c.page_url)
        with self.etlo.new.engine.begin() as conn:
            result = conn.execute(stmt)
            url_ids = [
                # Use the users_user_user_completed_pages name for 'page id'
                {"page_url": rw.page_url, "applicationpage_id": rw.id}
                for rw in result
            ]
        df_lookup = pd.DataFrame(data=url_ids)

        # Now join df_lookup onto df_completed to match `page_url` to `id`
        df_completed = df_completed.merge(
            df_lookup,
            on="page_url",
        )

        # Remove 'page_url' and insert into users_user_user_completed_pages
        del df_completed["page_url"]

        # Truncate then insert the data (rather than upsert). Because this is a
        # M2M table, all values must be unique
        truncate_stmt = delete(target_table)
        with self.etlo.new.engine.begin() as conn:
            conn.execute(truncate_stmt)
        self.etlo._update_autoincrement(
            target_table,
        )
        insert_stmt = insert(target_table).values(
            **{x: bindparam(x) for x in df_completed.columns}
        )
        with self.etlo.new.engine.begin() as conn:
            conn.execute(insert_stmt, df_completed.to_dict("records"))


class ETLToNew:
    def __init__(
        self,
        # Use the path to the default SQLite database as the default newdb_profile
        newdb_profile: str = str(
            Path(FILE_DIR)
            .joinpath("..", "..", "..", "get_your", "db.sqlite3")
            .resolve()
        ),
        newdb_monitor_profile: str = str(
            Path(FILE_DIR)
            .joinpath("..", "..", "..", "get_your", "db_monitor.sqlite3")
            .resolve()
        ),
        olddb_profile: str = "getfoco_prod_v6",
        olddb_analytics_profile: str = "getfoco_dev_analytics_v6",
        ignore_errors: bool = True,
    ):
        """
        Initialize the parameters needed to transfer from the old database.

        Parameters
        ----------
        newdb_profile : str, optional
            The coftc-cred-man profile with the proper credentials for the new
            database connection, or the path to a SQLite database. The default
            is the path to the default Django SQLite database.
        newdb_monitor_profile : str, optional
            The coftc-cred-man profile with the proper credentials for the new
            database 'monitor' connection, or the path to a SQLite database.
            The default is the path to the 'monitor' Django SQLite database.
        olddb_profile : str, optional
            The coftc-cred-man profile with the proper credentials for the old
            database connection, or the path to a SQLite database. The default
            is 'getfoco_prod_v6'.
        olddb_analytics_profile : str, optional
            The coftc-cred-man profile with the proper credentials for the old
            database 'analytics' connection, or the path to a SQLite database.
            The default is 'getfoco_dev_analytics_v6'.
        ignore_errors : bool, optional
            Specifies whether errors inserting specific records are to be
            ignored. The alternative is to rollback the entire transaction on a
            single-record error, leave the table unfilled, and abort the script.
            The default is True, which ignores single-record errors.

        Returns
        -------
        None

        """

        # Specify error handling
        self.ignore_errors = ignore_errors

        # Create SQLAlchemy connections
        self.new = DBMetadata(
            newdb_profile,
        )
        self.new_monitor = DBMetadata(
            newdb_monitor_profile,
        )
        self.old = DBMetadata(
            olddb_profile,
        )
        self.old_analytics = DBMetadata(
            olddb_analytics_profile,
        )

        # Initialize the table functions. Note that this must happen before the
        # table defintions are called
        self.table_functions = TableFunctions(self)

        # # Define static tables. These tables may not be truncated.
        # self.static_table_definitions = {
        #     '': {
        #         'source_table': '',
        #         'source_fields': [
        #         ],
        #         'target_fields': [
        #         ],
        #     },
        # }

        # Define dynamic tables and fill order (so that foreign key constraints
        # are followed). These tables may be truncated for testing (in reverse
        # order)
        self.dynamic_table_definitions = self.define_dynamic_tables()

        # Advise the user on truncating, then filling all available tables
        print(
            "ETL script initialized.\n"
            "To truncate then fill all 'dynamic tables', run fill_all_tables()"
        )

    def _get_table_index(
        self,
        target_table: str = None,
    ):
        """
        Get the index of the specified table within
        self.dynamic_table_definitions.

        Parameters
        ----------
        target_table : str, optional
            The target table name to start with for filling/truncating.

        Returns
        -------
        int
            Returns the index for self.dynamic_table_definitions.

        """

        if target_table is not None:
            # If specified, ensure starting_target_table is a string
            if not isinstance(target_table, str):
                raise TypeError("If included, target_table must be a string")

            # Find the index from a list of (ordered) table definition dict keys
            try:
                table_idx = list(self.dynamic_table_definitions.keys()).index(
                    target_table
                )
            except ValueError as exc:
                raise ValueError(
                    f"'{target_table}' is not a recognized target table name"
                ) from exc

        else:
            # If target_table is not specified, return None
            table_idx = None

        return table_idx

    def _update_autoincrement(
        self,
        target_table: Table,
        target_db: DBMetadata = None,
    ):
        """
        Update the specified table's auto-increment ``id`` value, if applicable.
        The auto-increment must be on a field named ``id``.

        Note that this is only for Postgres (target) tables.

        Parameters
        ----------
        target_table : Table
            The table to update autoincrement for.
        target_db : DBMetadata, optional
            The DBMetadata object to use for the transfer. If excluded (the
            default), ``self.new`` will be used.

        Returns
        -------
        None

        """

        # Gather the proper DBMetadata
        target_db = target_db or self.new

        # Ensure the database is supported
        if target_db.db_type not in ("postgres", "sqlite"):
            raise NotImplementedError(
                "The autoincrement-reset functionality is currently only available for PostgreSQL and SQLite."
            )

        # Check if the target table has values
        count_stmt = select(func.count(target_table.c.id))
        with target_db.engine.begin() as conn:
            count_val = conn.execute(count_stmt).fetchone()[0]

        try:
            if target_db.db_type == "postgres":
                # Get the Postgres sequence name
                sequence_name_stmt = text(
                    f"select pg_get_serial_sequence('{target_table.name}', 'id')"
                )
                with target_db.engine.begin() as conn:
                    sequence_name = conn.execute(sequence_name_stmt).fetchone()[0]

                # If the table has values, set the sequence to the value after
                # the max; else, set to 1 (using the 'false' param in setval())
                if count_val > 0:
                    sequence_stmt = text(
                        f"select setval('{sequence_name}', (select max(id) from {target_table.name}))"
                    )
                else:
                    sequence_stmt = text(f"select setval('{sequence_name}', 1, false)")
                with target_db.engine.begin() as conn:
                    conn.execute(sequence_stmt)

            else:
                # For SQLite, use the SQLITE_SEQUENCE table to update the next
                # autoincrement value
                sequence_table = Table(
                    "sqlite_sequence",
                    target_db.metadata,
                    autoload_with=target_db.engine,
                )

                # If the table has values, find the max ID; else, set to zero
                if count_val > 0:
                    max_id_stmt = select(func.max(target_table.c.id))
                    with target_db.engine.begin() as conn:
                        max_id = conn.execute(max_id_stmt).fetchone()[0]
                else:
                    max_id = 0

                # Set the sequence to the calculated max_id value (per SQLite's
                # standard)
                sequence_stmt = (
                    update(sequence_table)
                    .values(
                        seq=max_id,
                    )
                    .where(sequence_table.c.name == target_table.name)
                )
                with target_db.engine.begin() as conn:
                    conn.execute(sequence_stmt)

        except Exception as exc:
            raise Exception("Autoincrement could not be updated") from exc

    def cleanup(self):
        """Clean up the process (close connections), where applicable."""

        # Attempt to close each connection (fail silently on error)
        try:
            self.old.cleanup()
        except:
            pass
        try:
            self.new.cleanup()
        except:
            pass
        try:
            self.old_analytics.cleanup()
        except:
            pass
        try:
            self.new_monitor.cleanup()
        except:
            pass

    def port_data(
        self,
        source_table_name: str,
        target_table_name: str,
        source_db: DBMetadata = None,
        source_fields: Union[list, tuple] = (),
        target_db: DBMetadata = None,
        target_fields: Union[list, tuple] = (),
        target_types: Union[list, tuple] = (),
    ):
        """
        Port the data from 'source' to 'target'.

        Parameters
        ----------
        source_table_name : str
            Name of the source table.
        target_table_name : str
            Name of the target table.
        source_db : DBMetadata, optional
            The DBMetadata object to use for the transfer. If excluded (the
            default), ``self.old`` will be used.
        source_fields : Union[list, tuple], optional
            Ordered fields to pull from the source table. If excluded (the
            default), all fields from the source table will be used.
        target_db : DBMetadata, optional
            The DBMetadata object to use for the transfer. If excluded (the
            default), ``self.new`` will be used.
        target_fields : Union[list, tuple], optional
            Ordered fields to insert into the target table (matching the order
            of source_fields). If excluded (the default), all fields (and exact
            names) from the source table will be used.
        target_types : Union[list, tuple], optional
            Ordered datatypes for the data in the target table. This is only
            necessary if any datatypes are different than in the source table;
            the default is ().

        Returns
        -------
        None

        """

        # Gather the proper DBMetadata
        source_db = source_db or self.old
        target_db = target_db or self.new

        # Ensure the databases are supported
        if source_db.db_type not in ("postgres", "sqlite") or target_db.db_type not in (
            "postgres",
            "sqlite",
        ):
            raise NotImplementedError(
                "The UPSERT functionality used for the target table is currently only available for PostgreSQL and SQLite."
            )

        # Ensure all field/type inputs match
        if len(source_fields) != len(target_fields) or (
            target_types and len(source_fields) != len(target_types)
        ):
            raise AttributeError(
                "'source_fields', 'target_fields', and 'target_types' (if exists) must be the same length"
            )

        try:
            # First, load the source and target tables from metadata reflections
            source_table = Table(
                source_table_name,
                source_db.metadata,
                autoload_with=source_db.engine,
            )
            target_table = Table(
                target_table_name,
                target_db.metadata,
                autoload_with=target_db.engine,
            )

            # Define field mapping

            # If source_fields has no values, it means target_fields should be
            # equivalent; pull all fields from source_table and set them to
            # both source_ and target_fields
            if not source_fields:
                source_fields = target_fields = [x.name for x in source_table.columns]

            if target_types:
                mappings = [
                    {"source_field": src, "target_field": trg, "target_type": typ}
                    for src, trg, typ in zip(source_fields, target_fields, target_types)
                ]
            else:
                mappings = [
                    {"source_field": src, "target_field": trg}
                    for src, trg in zip(source_fields, target_fields)
                ]

            field_mapping = FieldMapping(mappings=mappings)

            # Gather the field if source_value is None, otherwise use the
            # (literal) source_value labeled as the field name
            source_table_fields = [
                source_table.c.get(fd)
                if vl is None
                else literal_column("NULL").label(fd)
                if vl == ""
                else literal_column(str(vl)).label(fd)
                for fd, vl in field_mapping.source_values.items()
            ]

            # If field_mapping.target_types DNE, define it as the types in
            # source_table_fields, using the DTYPE_MAPPING defined at the top
            # of this file (this is to resolve the issue of 'int' dtypes in
            # pandas not being about to store NULL values)
            if not field_mapping.target_types:
                # Convert each Postgres dtype to Python
                python_dtypes = [
                    next(
                        ptype
                        for dbtype, ptype in DTYPE_MAPPING.items()
                        if re.match(dbtype, str(x.type))
                    )
                    if isinstance(x, Column)
                    else "str"
                    for x in source_table_fields
                ]

                # Just recreate field_mapping rather than do a bunch of update()
                field_mapping = FieldMapping(
                    mappings=[
                        {"source_field": src, "target_field": trg, "target_type": typ}
                        for src, trg, typ in zip(
                            source_fields, target_fields, python_dtypes
                        )
                    ]
                )

            # Overwrite the source fields, given any new data from field_mapping
            source_table_fields = [
                source_table.c.get(fd)
                if vl is None
                else literal_column("NULL").label(fd)
                if vl == ""
                else literal_column(str(vl)).label(fd)
                for fd, vl in field_mapping.source_values.items()
            ]

            # Define the SELECT statement
            stmt = select(*source_table_fields)

            # Pull the data into a DataFrame and process it
            df = process_data(stmt, source_db.engine, field_mapping)

            # # Add records
            # column_length = len(df)
            # df = df.assign(
            #     is_active=column_length*[True],
            #     created_at=column_length*[self.now],
            #     created_by=column_length*['UpdatedFromJDE'],
            # )

            # Finalize df for database upsert
            df = finalize_df_for_database(df, db_fields=source_table_fields)

            try:
                # Find the primary key(s) to upsert with
                primary_keys = [x.name for x in target_table.columns if x.primary_key]

                # Use MERGE to upsert if the target is Postgres; else use
                # ON CONFLICT
                if target_db.db_type == "postgres":
                    upsert_via_merge(
                        target_db,
                        target_table,
                        df,
                        primary_keys,
                    )

                else:
                    # Upsert (insert with ON CONFLICT DO UPDATE) the data. This
                    # operation is specific to Postgres, but works with SQLite
                    # as well
                    upsert_stmt = insert(target_table).values(
                        # Use all columns in df
                        **{x: bindparam(x) for x in df.columns}
                    )

                    upsert_stmt = upsert_stmt.on_conflict_do_update(
                        index_elements=primary_keys,
                        # Set all columns except the primary keys
                        set_={
                            x: bindparam(x) for x in df.columns if x not in primary_keys
                        },
                    )
                    with target_db.engine.connect() as conn:
                        conn.execute(upsert_stmt, df.to_dict("records"))
                        conn.commit()

            except Exception as exc:
                # If ignore_errors is specified, proceed with the *slow*
                # row-by-row insert (ONLY) (after notifying user)
                # This allows rejecting specific records on failure
                if self.ignore_errors:
                    print(
                        f"Bulk UPSERT failed with\n\n{exc}\n\nProceeding with much slower row-by-row INSERT (ONLY)..."
                    )

                    ignore_count = 0
                    insert_stmt = insert(target_table).values(
                        # Use all columns in df
                        **{x: bindparam(x) for x in df.columns}
                    )
                    for row in df.to_dict("records"):
                        try:
                            with target_db.engine.connect() as conn:
                                conn.execute(insert_stmt, row)
                                conn.commit()
                        except:
                            ignore_count += 1

                    print(
                        f"Row-by-row insertion successful! {ignore_count} of {len(df)} records ignored."
                    )

                else:
                    # Raise the original error after notifying user that
                    # specifying ignore_errors may be able to bypass the
                    # issue
                    print(
                        "The following error was raised during bulk UPSERT (setting ignore_errors=True may be able to load partial data):"
                    )
                    raise

        except:
            raise

        else:
            return (source_table, target_table)

    def truncate_dynamic_tables(
        self,
        starting_target_table: str = None,
        ending_target_table: str = None,
    ):
        """
        Truncate all available DEV tables (e.g. "dynamic" tables) beginning with
        ``starting_target_table`` (if exists).

        Parameters
        ----------
        source_db : DBMetadata, optional
            The DBMetadata object to use for the transfer. If excluded (the
            default), ``self.old`` will be used.
        target_db : DBMetadata, optional
            The DBMetadata object to use for the transfer. If excluded (the
            default), ``self.new`` will be used.
        starting_target_table : str, optional
            Specifies the table in the target database to start the process
            with. Table order (in self.dynamic_table_definitions) is preserved
            (and truncation is a reverse of this order); this just ignores all
            tables prior to this value. The default is None, specifying that all
            tables will be included.
        ending_target_table : str, optional
            Specifies the table in the target database to end the process
            with. Table order (in self.dynamic_table_definitions) is preserved
            (and truncation is a reverse of this order); this just ignores all
            tables *after* to this value (note that this is inclusive, so a
            table specified here will be included). The default is None,
            specifying that all tables will be included.

        Returns
        -------
        None.

        """

        # Format custom portion of the truncation message
        custom_truncate_msg = ""
        if starting_target_table is not None:
            custom_truncate_msg += f"starting at '{starting_target_table}'"
        if ending_target_table is not None:
            custom_truncate_msg += f", ending with '{ending_target_table}'"

        # Gather indices (default to 0 or total length, respectively, if the
        # target_table isn't specified)
        starting_idx = (
            self._get_table_index(
                target_table=starting_target_table,
            )
            or 0
        )
        ending_idx = self._get_table_index(
            target_table=ending_target_table,
        )
        # 0 === None for the format used in starting_idx; ending_idx needs to be
        # calculated explicitly so that only None is replaced with the max index
        ending_idx = (
            ending_idx
            if ending_idx is not None
            else len(self.dynamic_table_definitions)
        )

        # Print truncation message
        print(
            "Beginning table truncation{cst}...".format(
                cst=f" ({custom_truncate_msg})" if custom_truncate_msg else "",
            )
        )

        # Include all dynamic tables, beginning with starting_idx and ending
        # with ending_idx (inclusive)
        table_names = [
            (dct["target_db"] if "target_db" in dct else self.new, nm)
            for idx, (nm, dct) in enumerate(self.dynamic_table_definitions.items())
            if idx >= starting_idx and idx <= ending_idx
        ]

        # Group tables by database
        unique_dbs = set(x[0] for x in table_names)
        tables_to_truncate = {key: [] for key in unique_dbs}
        for itm in table_names:
            tables_to_truncate[itm[0]].append(itm[1])

        # Ensure all databases are supported
        if any(x.db_type not in ("postgres", "sqlite") for x in tables_to_truncate):
            raise NotImplementedError(
                "The truncate functionality is currently only available for PostgreSQL and SQLite."
            )

        for dbm, tbls in tables_to_truncate.items():
            # If SQLite, use the SQLAlchemy option; else, use Postgres with
            # error-checking
            if dbm.db_type == "sqlite":
                # Use the SQLITE_SEQUENCE table to update the next autoincrement
                # value
                sequence_table = Table(
                    "sqlite_sequence",
                    dbm.metadata,
                    autoload_with=dbm.engine,
                )

                for tbl in tbls:
                    target_table = Table(
                        tbl,
                        dbm.metadata,
                        autoload_with=dbm.engine,
                    )
                    # Delete all from the table, then reset auto-increment
                    delete_stmt = delete(target_table)

                    # Set the sequence to the calculated max_id value (per SQLite's
                    # standard)
                    reset_autoincrement_stmt = (
                        update(sequence_table)
                        .values(
                            seq=0,
                        )
                        .where(sequence_table.c.name == target_table.name)
                    )

                    with dbm.engine.begin() as conn:
                        conn.execute(delete_stmt)
                        conn.execute(reset_autoincrement_stmt)

            else:
                # Attempt to truncate all specified tables simultaneously
                try:
                    delete_stmt = text(
                        "truncate {} restart identity".format(
                            ", ".join([f"public.{x}" for x in tbls])
                        )
                    )
                    with dbm.engine.begin() as conn:
                        conn.execute(delete_stmt)

                except FeatureNotSupported as exc:
                    # Extract the error message and rollback the connection
                    error_msg = exc.args[0]

                    # Attempt to parse the error. If error_msg startswith
                    # case-insensitive 'cannot truncate'...
                    if re.match("cannot truncate", error_msg, re.I):
                        # Find the 'detail' section and return the table name
                        reftable_name_re = re.search(
                            r'detail:\s+table\s+"(.*?)"',
                            error_msg,
                            re.I,
                        )

                        # Re-raise the exception with a custom message, if applicable
                        try:
                            reftable_name = reftable_name_re.groups(1)[0]
                        except:
                            # Pass this along to the outer 'raise'
                            pass
                        else:
                            # Notify of additional errors or messages, depending on the
                            # placement of reftable in dynamic_table_definitions
                            reftable_index = list(
                                self.dynamic_table_definitions.keys()
                            ).index(reftable_name)
                            if reftable_index <= ending_idx:
                                additional_notification = f'\n\nAdditional error: "{reftable_name}" is defined *before* "{tbls[-1]}"; this will need to be rearranged before proceeding.'
                            elif reftable_index != ending_idx + 1:
                                additional_notification = f'\n\nAdditionally: consider moving "{reftable_name}" to directly after "{tbls[-1]}" in the dynamic table definitions to simplify the ETL.'
                            else:
                                additional_notification = ""

                            raise FeatureNotSupported(
                                f"""Update the command to use "ending_target_table='{reftable_name}'" to resolve this issue: table "{tbls[-1]}" could not be truncated.{additional_notification}"""
                            ) from exc
                    raise

        print("Truncation successful!")

    def define_dynamic_tables(self):
        """
        Define the dynamic tables (e.g. those that can be truncated and
        rebuilt), along with how the tables should be ported from legacy.

        Each top-level key is a table name with a dict defined under it.
        Keys in this dict are:
            - source_table (optional): Defines the source table for a direct
            data transfer. If this is excluded, there will be no direct transfer
            from old to new tables
            - source_fields (optional): Defines the (ordered) fields to be read
            from source_table
            - target_fields (optional): Defines the fields in the target table
            that each source field will be transferred to. The order of these
            must match that of source_fields
            - target_dtypes (optional): Defines the datatype for each target
            field. This is only necessary if the datatypes are not the same as
            the source table, BUT all fields must be included here if the key
            exists
            - after_port (optional): A list of tasks to run. These are run after
            a direct transfer, and also independently (e.g. these will be run
            regardless of whether a direct transfer was defined). Keys in this
            dict are:
                - function: The function to execute. Note that this isn't just
                the function name, it's an instantiation of that function
                without calling it
                - kwargs: Any keyword arguments expected by the above function.
                Use an empty dictionary if no kwargs are used.

        All tables that have no associated data (e.g. are defined to an empty
        dict) are accounted for elsewhere and are only included here to denote
        that they are available for truncation (if truncate_dynamic_tables() is
        run).

        Rubric for new table:
            "<app name>_<lowercase model name>": {
                "source_table": "",
                "source_fields": [
                ],
                "target_fields": [
                ],
                "target_types": [
                ],
                "after_port": [{
                    "function": ,
                    "kwargs": {},
                }],
            },

        """

        table_defs = {
            # Truncate (only) tables that FK to users_user (or themselves)
            "django_admin_log": {},
            "mfa_authenticator": {},
            "socialaccount_socialtoken": {},
            "socialaccount_socialaccount": {},
            "users_user_user_completed_pages": {},
            "users_user": {
                "source_table": "app_user",
                "source_fields": [
                    "id",
                    "password",
                    "last_login",
                    "is_superuser",
                    "is_staff",
                    "is_active",
                    "date_joined",
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "has_viewed_dashboard",
                    "is_updated",
                    "last_completed_at",
                    "last_action_notification_at",
                ],
                "target_fields": [
                    "id",
                    "password",
                    "last_login",
                    "is_superuser",
                    "is_staff",
                    "is_active",
                    "date_joined",
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "has_viewed_dashboard",
                    "user_has_updated",
                    "last_completed_at",
                    "last_action_notification_at",
                ],
                "after_port": [
                    {
                        "function": self.table_functions.determine_completed_pages,
                        "kwargs": {},
                    },
                ],
            },
            # This table has an FK on account_emailaddress
            "account_emailconfirmation": {},
            "account_emailaddress": {
                "source_table": "app_user",
                "source_fields": [
                    "id",
                    "email",
                    # Use non-strings to denote that a constant should be used
                    True,
                    True,
                ],
                "target_fields": [
                    "user_id",
                    "email",
                    "verified",
                    "primary",
                ],
            },
            "auth_group": {
                "source_table": "auth_group",
            },
            "auth_permission": {
                "source_table": "auth_permission",
            },
            "users_user_groups": {
                "source_table": "app_user_groups",
            },
            "users_user_user_permissions": {
                "source_table": "app_user_user_permissions",
            },
            "users_usernote": {
                "source_table": "app_admin",
            },
            "auth_group_permissions": {
                "source_table": "auth_group_permissions",
            },
            "ref_iqprogram": {
                "source_table": "app_iqprogramrd",
                "source_fields": [
                    "id",
                    "created_at",
                    "modified_at",
                    "program_name",
                    "ami_threshold",
                    "friendly_name",
                    "friendly_category",
                    "friendly_description",
                    "friendly_supplemental_info",
                    "learn_more_link",
                    "friendly_eligibility_review_period",
                    "enable_autoapply",
                    "renewal_interval_year",
                    "requires_is_city_covered",
                    "requires_is_in_gma",
                    "is_active",
                    "",
                ],
                "target_fields": [
                    "id",
                    "created_at",
                    "modified_at",
                    "program_name",
                    "ami_threshold",
                    "friendly_name",
                    "friendly_category",
                    "friendly_description",
                    "friendly_supplemental_info",
                    "learn_more_link",
                    "friendly_eligibility_review_period",
                    "enable_autoapply",
                    "renewal_interval_year",
                    "requires_is_city_covered",
                    "requires_is_in_gma",
                    "is_active",
                    "additional_external_form_link",
                ],
            },
            "ref_eligibilityprogram": {
                "source_table": "app_eligibilityprogramrd",
                "source_fields": [
                    "id",
                    "created_at",
                    "modified_at",
                    "program_name",
                    "ami_threshold",
                    "friendly_name",
                    "friendly_description",
                    "is_active",
                ],
                "target_fields": [
                    "id",
                    "created_at",
                    "modified_at",
                    "program_name",
                    "ami_threshold",
                    "friendly_name",
                    "friendly_description",
                    "is_active",
                ],
            },
            "ref_address": {
                "source_table": "app_addressrd",
            },
            "app_iqprogram": {
                "source_table": "app_iqprogram",
            },
            "app_household": {
                "source_table": "app_household",
                "source_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "is_updated",
                    "is_income_verified",
                    "duration_at_address",
                    "number_persons_in_household",
                    "income_as_fraction_of_ami",
                    "rent_own",
                ],
                "target_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "user_has_updated",
                    "is_income_verified",
                    "duration_at_address",
                    "number_persons_in_household",
                    "income_as_fraction_of_ami",
                    "rent_own",
                ],
            },
            "app_householdmembers": {
                "source_table": "app_householdmembers",
                "source_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "household_info",
                    "is_updated",
                ],
                "target_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "household_info",
                    "user_has_updated",
                ],
            },
            "app_eligibilityprogram": {
                "source_table": "app_eligibilityprogram",
            },
            "app_address": {
                "source_table": "app_address",
                "source_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "eligibility_address_id",
                    "mailing_address_id",
                    "is_updated",
                ],
                "target_fields": [
                    "created_at",
                    "modified_at",
                    "user_id",
                    "eligibility_address_id",
                    "mailing_address_id",
                    "user_has_updated",
                ],
            },
            "dashboard_feedback": {
                "source_table": "app_feedback",
                "source_fields": [
                    "id",
                    "created",
                    "modified",
                    "star_rating",
                    "feedback_comments",
                ],
                "target_fields": [
                    "id",
                    "created_at",
                    "modified_at",
                    "star_rating",
                    "feedback_comments",
                ],
            },
            "monitor_loglevel": {
                "source_table": "logger_levelrd",
                "source_db": self.old_analytics,
                "target_db": self.new_monitor,
            },
            "monitor_logdetail": {
                "source_table": "logger_detail",
                "source_db": self.old_analytics,
                "target_db": self.new_monitor,
            },
        }

        return table_defs

    def fill_all_tables(
        self,
        starting_target_table: str = None,
        ending_target_table: str = None,
        truncate_first: bool = True,
    ):
        """
        Fill all target tables, using functions defined for each table.

        Parameters
        ----------
        starting_target_table : str, optional
            Specifies the table in the target database to start the process
            with. This applies to truncation as well as fill (if
            ``truncate_first`` (below) is specified). Table order (in
            self.dynamic_table_definitions) is preserved, this just ignores all
            tables prior to this value. The default is None, specifying that
            all tables will be included.
        ending_target_table : str, optional
            Specifies the table in the target database to end the process
            with. Table order (in self.dynamic_table_definitions) is preserved
            (and truncation is a reverse of this order); this just ignores all
            tables *after* to this value (note that this is inclusive, so a
            table specified here will be included). The default is None,
            specifying that all tables will be included.
        truncate_first : bool, optional
            Truncate all tables before filling, beginning with
            ``starting_target_table``, if designated. The default is True.

        Returns
        -------
        None.

        """

        # Gather indices (default to 0 or total length, respectively, if the
        # target_table isn't specified)
        starting_idx = (
            self._get_table_index(
                target_table=starting_target_table,
            )
            or 0
        )
        ending_idx = self._get_table_index(
            target_table=ending_target_table,
        )
        # 0 === None for the format used in starting_idx; ending_idx needs to be
        # calculated explicitly so that only None is replaced with the max index
        ending_idx = (
            ending_idx
            if ending_idx is not None
            else len(self.dynamic_table_definitions)
        )

        # If specified, truncate tables in self.dynamic_table_definitions, using
        # starting_target_table and afterward
        if truncate_first:
            self.truncate_dynamic_tables(
                starting_target_table=starting_target_table,
                ending_target_table=ending_target_table,
            )

        # Fill tables in order of self.dynamic_table_definitions, starting with
        # starting_idx
        for flidx, (tblnm, tbldef) in enumerate(self.dynamic_table_definitions.items()):
            # Start at starting_target_table (skip the loop until starting_idx
            # is met)
            if flidx < starting_idx:
                continue

            print(f"Beginning port of '{tblnm}'...")

            # Port data if 'source_table' exists
            if "source_table" in tbldef.keys():
                source_table, target_table = self.port_data(
                    source_table_name=tbldef["source_table"],
                    target_table_name=tblnm,
                    source_db=tbldef["source_db"] if "source_db" in tbldef else None,
                    source_fields=tbldef["source_fields"]
                    if "source_fields" in tbldef
                    else (),
                    target_db=tbldef["target_db"] if "target_db" in tbldef else None,
                    target_fields=tbldef["target_fields"]
                    if "target_fields" in tbldef
                    else (),
                    target_types=tbldef["target_types"]
                    if "target_types" in tbldef
                    else (),
                )
                print("Port complete")

            # Run all functions defined in 'after_port', if exists
            if "after_port" in tbldef.keys():
                for aftritm in tbldef["after_port"]:
                    print(f"Running '{aftritm['function'].__name__}()'...")
                    # Note that all 'after_port' functions must return
                    # target_table
                    target_table = aftritm["function"](**aftritm["kwargs"])
                    print("Run complete")

            # Update auto-increment to be the value after the max, if applicable
            try:
                self._update_autoincrement(
                    target_table,
                    target_db=tbldef["target_db"] if "target_db" in tbldef else None,
                )
            except (UnboundLocalError, AttributeError):
                # Case for if target_table was not defined or if there is no
                # 'id' column
                pass

            print(f"'{tblnm}' fill successful!")

            # Break the loop once ending_idx has been reached, if applicable
            if flidx >= ending_idx:
                break

        # Clean up the connections before finishing
        self.cleanup()

        print("fill_all_tables complete and connections closed")
