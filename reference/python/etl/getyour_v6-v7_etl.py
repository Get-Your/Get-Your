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

# from psycopg.errors import UniqueViolation
from psycopg.errors import FeatureNotSupported
from sqlalchemy import (
    Table,
    bindparam,
    delete,
    func,
    select,
    text,
    update,
)

# from sqlalchemy.exc import IntegrityError, NoSuchTableError
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


class ETLToNew:
    def __init__(
        self,
        # Use the path to the default SQLite database as the default newdb_profile
        newdb_profile: str = str(
            Path(FILE_DIR)
            .joinpath("..", "..", "..", "get_your", "db.sqlite3")
            .resolve()
        ),
        olddb_profile: str = "getfoco_prod_v6",
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
        olddb_profile : str, optional
            The coftc-cred-man profile with the proper credentials for the old
            database connection, or the path to a SQLite database. The default
            is 'getfoco_prod_v6'.
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
        self.old = DBMetadata(
            olddb_profile,
        )

        # # Initialize the table functions. Note that this must happen before the
        # # table defintions are called
        # self.table_functions = TableFunctions(self)

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
    ):
        """
        Update the specified table's auto-increment ``id`` value, if applicable.
        The auto-increment must be on a field named ``id``.

        Note that this is only for Postgres (target) tables.

        Parameters
        ----------
        target_table : Table
            The table to update autoincrement for.

        Returns
        -------
        None

        """

        if self.new.db_type not in ("postgres", "sqlite"):
            raise NotImplementedError(
                "The autoincrement-reset functionality is currently only available for PostgreSQL and SQLite."
            )

        # Check if the target table has values
        count_stmt = select(func.count(target_table.c.id))
        with self.new.engine.begin() as conn:
            count_val = conn.execute(count_stmt).fetchone()[0]

        try:
            if self.new.db_type == "postgres":
                # Get the Postgres sequence name
                sequence_name_stmt = text(
                    f"select pg_get_serial_sequence('{target_table.name}', 'id')"
                )
                with self.new.engine.begin() as conn:
                    sequence_name = conn.execute(sequence_name_stmt).fetchone()[0]

                # If the table has values, set the sequence to the value after
                # the max; else, set to 1 (using the 'false' param in setval())
                if count_val > 0:
                    sequence_stmt = text(
                        f"select setval('{sequence_name}', (select max(id) from {target_table.name}))"
                    )
                else:
                    sequence_stmt = text(f"select setval('{sequence_name}', 1, false)")
                with self.new.engine.begin() as conn:
                    conn.execute(sequence_stmt)

            else:
                # For SQLite, use the SQLITE_SEQUENCE table to update the next
                # autoincrement value
                sequence_table = Table(
                    "sqlite_sequence",
                    self.new.metadata,
                    autoload_with=self.new.engine,
                )

                # If the table has values, find the max ID; else, set to zero
                if count_val > 0:
                    max_id_stmt = select(func.max(target_table.c.id))
                    with self.new.engine.begin() as conn:
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
                with self.new.engine.begin() as conn:
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

    def port_data(
        self,
        source_table_name: str,
        target_table_name: str,
        source_fields: Union[list, tuple] = (),
        target_fields: Union[list, tuple] = (),
        target_types: Union[list, tuple] = (),
    ):
        """
        Port the data from 'source' to 'target'.

        Parameters
        ----------
        source_table_name : str
            Name of the source table.
        source_fields : Union[list, tuple]
            Ordered fields to pull from the source table.
        target_table_name : str
            Name of the target table.
        target_fields : Union[list, tuple]
            Ordered fields to insert into the target table (matching the order
            of source_fields).
        target_types : Union[list, tuple], optional
            Ordered datatypes for the data in the target table. This is only
            necessary if any datatypes are different than in the source table;
            the default is ().

        Returns
        -------
        None

        """

        if self.new.db_type not in ("postgres", "sqlite"):
            raise NotImplementedError(
                "The UPSERT functionality used for the target table is currently only available for PostgreSQL and SQLite."
            )

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
                self.old.metadata,
                autoload_with=self.old.engine,
            )
            target_table = Table(
                target_table_name,
                self.new.metadata,
                autoload_with=self.new.engine,
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

            stmt = select(
                *[source_table.c.get(x) for x in field_mapping.source_fields.keys()],
            )

            # Pull the data into a DataFrame and process it
            df = process_data(stmt, self.old.engine, field_mapping)

            # # Add records
            # column_length = len(df)
            # df = df.assign(
            #     is_active=column_length*[True],
            #     created_at=column_length*[self.now],
            #     created_by=column_length*['UpdatedFromJDE'],
            # )

            # Finalize df for database upsert
            df = finalize_df_for_database(df)

            try:
                # Use MERGE to upsert if the target is Postgres; else use
                # ON CONFLICT
                if self.new.db_type == "postgres":
                    upsert_via_merge(
                        self.new,
                        target_table,
                        df,
                        [x.name for x in target_table.columns if x.primary_key],
                    )

                else:
                    # Upsert (insert with ON CONFLICT DO UPDATE) the data. This
                    # operation is specific to Postgres, but works with SQLite
                    # as well
                    upsert_stmt = insert(target_table).values(
                        # Use all columns in df
                        **{x: bindparam(x) for x in df.columns}
                    )

                    # Try the ON CONFLICT DO UPDATE first with 'id', then with
                    # 'user_id' if that fails
                    try:
                        upsert_stmt = upsert_stmt.on_conflict_do_update(
                            index_elements=[target_table.c.id],
                            # Set all columns except 'id'
                            set_={x: bindparam(x) for x in df.columns if x != "id"},
                        )
                    except AttributeError:
                        upsert_stmt = upsert_stmt.on_conflict_do_update(
                            index_elements=[target_table.c.user_id],
                            # Set all columns except 'id'
                            set_={
                                x: bindparam(x) for x in df.columns if x != "user_id"
                            },
                        )
                    with self.new.engine.connect() as conn:
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
                            with self.new.engine.connect() as conn:
                                conn.execute(insert_stmt, row)
                                conn.commit()
                        except:
                            ignore_count += 1

                    print(
                        f"Row-by-row insertion successful! {ignore_count} records ignored."
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

        if self.new.db_type not in ("postgres", "sqlite"):
            raise NotImplementedError(
                "The truncate functionality is currently only available for PostgreSQL and SQLite."
            )

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
            x
            for idx, x in enumerate(self.dynamic_table_definitions.keys())
            if idx >= starting_idx and idx <= ending_idx
        ]

        # If SQLite, use the SQLAlchemy option; else, use Postgres with
        # error-checking
        if self.new.db_type == "sqlite":
            # Use the SQLITE_SEQUENCE table to update the next autoincrement
            # value
            sequence_table = Table(
                "sqlite_sequence",
                self.new.metadata,
                autoload_with=self.new.engine,
            )

            for tbl in table_names:
                target_table = Table(
                    tbl,
                    self.new.metadata,
                    autoload_with=self.new.engine,
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

                with self.new.engine.begin() as conn:
                    conn.execute(delete_stmt)
                    conn.execute(reset_autoincrement_stmt)

        else:
            # Attempt to truncate all specified tables simultaneously
            try:
                delete_stmt = text(
                    "truncate {} restart identity".format(
                        ", ".join([f"public.{x}" for x in table_names])
                    )
                )
                with self.new.engine.begin() as conn:
                    conn.execute(delete_stmt)

            except FeatureNotSupported as exc:
                # Extract the error message and rollback the connection
                error_msg = exc.args[0]
                self.target_conn.rollback()

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
                            additional_notification = f'\n\nAdditional error: "{reftable_name}" is defined *before* "{table_names[-1]}"; this will need to be rearranged before proceeding.'
                        elif reftable_index != ending_idx + 1:
                            additional_notification = f'\n\nAdditionally: consider moving "{reftable_name}" to directly after "{table_names[-1]}" in the dynamic table definitions to simplify the ETL.'
                        else:
                            additional_notification = ""

                        raise FeatureNotSupported(
                            f"""Update the command to use "ending_target_table='{reftable_name}'" to resolve this issue: table "{table_names[-1]}" could not be truncated.{additional_notification}"""
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
            '<app name>_<lowercase model name>': {
                'source_table': '',
                'source_fields': [
                ],
                'target_fields': [
                ],
                'target_types': [
                ],
                'after_port': [{
                    'function': ,
                    'kwargs': {},
                }],
            },

        """

        table_defs = {}

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
        ) or len(self.dynamic_table_definitions)

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
                    source_fields=tbldef["source_fields"]
                    if "source_fields" in tbldef
                    else (),
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
                self._update_autoincrement(target_table)
            except AttributeError:
                # Case for if there is no 'id' column
                pass

            print(f"'{tblnm}' fill successful!")

            # Break the loop once ending_idx has been reached, if applicable
            if flidx >= ending_idx:
                break

        # Clean up the connections before finishing
        self.cleanup()

        print("fill_all_tables complete and connections closed")
