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

import re

import pandas as pd
from coftc_db_utils.sqlalchemy_functions import DBMetadata
from coftc_db_utils.sqlalchemy_functions import FieldMapping
from coftc_db_utils.sqlalchemy_functions import finalize_df_for_database
from coftc_db_utils.sqlalchemy_functions import process_data
from coftc_db_utils.sqlalchemy_functions import upsert_via_merge
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import bindparam
from sqlalchemy import cast
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select

# Use Postgres-specific insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.sqltypes import BOOLEAN
from sqlalchemy.sql.sqltypes import VARCHAR


class TableFunctions:
    def __init__(
        self,
        etl_object,
        dtype_mapping: list | tuple,
        *,
        # The following are keyword-only
        ignore_errors: bool = False,
    ):
        """Table-specific functions for the ETL process."""
        self.etlo = etl_object
        self.ignore_errors = ignore_errors

        self.dtype_mapping = dtype_mapping

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
                    cast(
                        source_eligibilityprogram_table.c.document_path == "",
                        Integer,
                    ),
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
                    ],
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
                    ],
                )

                if user_id in address_exists_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:address"},
                    )
                if user_id in household_exists_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:household"},
                    )
                if user_id in householdmembers_exists_dict:
                    complete_pages.append(
                        {
                            "user_id": user_id,
                            "page_url": "app:household_members",
                        },
                    )
                # Check to see if the user has selected any eligibility programs
                if user_id in empty_uploads_dict:
                    complete_pages.append(
                        {"user_id": user_id, "page_url": "app:programs"},
                    )
                    # Check if any of the eligibility programs have empty uploads
                    if empty_uploads_dict[user_id] == 0:
                        complete_pages.append(
                            {"user_id": user_id, "page_url": "app:files"},
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
            **{x: bindparam(x) for x in df_completed.columns},
        )
        with self.etlo.new.engine.begin() as conn:
            conn.execute(insert_stmt, df_completed.to_dict("records"))

    def port_user_table(self):
        def _query_source_table(
            source_db: DBMetadata,
            source_table: Table,
            map_list: list | tuple,
        ):
            # Gather the field if source_value
            source_table_fields = [
                source_table.c.get(x["source_field"]) for x in map_list
            ]

            # Define 'target_types' as the types in source_table_fields, using
            # the dtype_mapping passed in via ETLToNew() (this is to
            # resolve the issue of 'int' dtypes in pandas not being about to
            # store NULL values)
            python_dtypes = [
                next(
                    iter(
                        ptype
                        for dbtype, ptype in self.dtype_mapping.items()
                        if re.match(dbtype, str(x.type))
                    ),
                    None,
                )
                if isinstance(x, Column)
                else "str"
                for x in source_table_fields
            ]

            # Create field_mapping
            field_mapping = FieldMapping(
                mappings=[
                    {
                        "source_field": mp["source_field"],
                        "target_field": mp["target_field"],
                        "target_type": typ,
                    }
                    for mp, typ in zip(
                        map_list,
                        python_dtypes,
                    )
                ],
            )

            # Overwrite the source fields, given any new data from field_mapping
            source_table_fields = [
                source_table.c.get(fd) for fd, _ in field_mapping.source_fields.items()
            ]

            # Define the SELECT statement
            stmt = select(*source_table_fields)

            # Pull the data into a DataFrame and process it
            df = process_data(
                stmt,
                source_db.engine,
                field_mapping,
                do_follow_django=True,
            )

            # Find the 'char' fields, for reference later
            char_fields = [
                fd for fd, tp in field_mapping.target_types.items() if tp == "str"
            ]

            return (char_fields, df)

        # Ensure the databases are supported
        if self.etlo.old.db_type not in (
            "postgres",
            "sqlite",
        ) or self.etlo.new.db_type not in (
            "postgres",
            "sqlite",
        ):
            raise NotImplementedError(
                "The UPSERT functionality used for the target table is currently only available for PostgreSQL and SQLite.",
            )

        try:
            # First, load the source and target tables from metadata reflections
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
            target_table = Table(
                "users_user",
                self.etlo.new.metadata,
                autoload_with=self.etlo.new.engine,
            )

            # Define field mapping for each table
            user_map_list = [
                {"source_field": "id", "target_field": "id"},
                {"source_field": "password", "target_field": "password"},
                {"source_field": "last_login", "target_field": "last_login"},
                {"source_field": "is_superuser", "target_field": "is_superuser"},
                {"source_field": "is_staff", "target_field": "is_staff"},
                {"source_field": "is_active", "target_field": "is_active"},
                {"source_field": "is_archived", "target_field": "is_archived"},
                {"source_field": "date_joined", "target_field": "date_joined"},
                {"source_field": "email", "target_field": "email"},
                {"source_field": "first_name", "target_field": "first_name"},
                {"source_field": "last_name", "target_field": "last_name"},
                {"source_field": "phone_number", "target_field": "phone_number"},
                {
                    "source_field": "has_viewed_dashboard",
                    "target_field": "has_viewed_dashboard",
                },
                {"source_field": "is_updated", "target_field": "user_has_updated"},
                {
                    "source_field": "last_completed_at",
                    "target_field": "last_completed_at",
                },
                {
                    "source_field": "last_action_notification_at",
                    "target_field": "last_action_notification_at",
                },
            ]
            address_map_list = [
                {"source_field": "user_id", "target_field": "id"},
                {
                    "source_field": "eligibility_address_id",
                    "target_field": "eligibility_address_id",
                },
                {
                    "source_field": "mailing_address_id",
                    "target_field": "mailing_address_id",
                },
            ]
            household_map_list = [
                {"source_field": "user_id", "target_field": "id"},
                {
                    "source_field": "is_income_verified",
                    "target_field": "is_income_verified",
                },
                {
                    "source_field": "duration_at_address",
                    "target_field": "duration_at_address",
                },
                {
                    "source_field": "income_as_fraction_of_ami",
                    "target_field": "income_as_fraction_of_ami",
                },
                {"source_field": "rent_own", "target_field": "rent_own"},
            ]

            # Fill the beginnings of the user table
            char_fields, df = _query_source_table(
                self.etlo.old,
                source_user_table,
                user_map_list,
            )

            # Combine with the address table (on id)
            char_fields_add, df_add = _query_source_table(
                self.etlo.old,
                source_address_table,
                address_map_list,
            )
            # Join the address table to the primary DataFrame
            df = df.merge(
                df_add,
                # Make a 'left' merge so that df keeps all values
                how="left",
                # Merge on 'id' field
                on="id",
            )
            char_fields += char_fields_add

            # Combine with the household table (on id)
            char_fields_add, df_add = _query_source_table(
                self.etlo.old,
                source_household_table,
                household_map_list,
            )
            # Join the household table to the primary DataFrame
            df = df.merge(
                df_add,
                # Make a 'left' merge so that df keeps all values
                how="left",
                # Merge on 'id' field
                on="id",
            )
            char_fields += char_fields_add

            # Fill merged fields that DNE with that column's default value
            # Postgres uses the 'server_default' option instead of 'default',
            # which is slightly more intricate to parse
            for col in target_table.columns:
                if not col.nullable:
                    default_value = col.default
                    if (
                        not default_value
                        and col.server_default
                        and col.server_default.has_argument
                    ):
                        if isinstance(col.type, BOOLEAN):
                            default_value = (
                                col.server_default.arg.text.lower() == "true"
                            )
                        elif isinstance(col.type, VARCHAR):
                            default_value = (
                                ""
                                if col.server_default.arg.text.startswith("''")
                                else col.server_default.arg.text
                            )

                    if default_value is not None:
                        df[col.name] = df[col.name].apply(
                            lambda x: default_value if pd.isna(x) else x,
                        )

            # Convert merged fields that DNE from None to '' (empty string) for
            # all 'char' fields (to follow Django guidelines)
            for fd in char_fields:
                df[fd] = df[fd].apply(lambda x: "" if pd.isna(x) else x)

            try:
                # Find the primary key(s) to upsert with
                primary_keys = [x.name for x in target_table.columns if x.primary_key]

                # Use MERGE to upsert if the target is Postgres or SQLite; else
                # use ON CONFLICT
                if self.etlo.new.db_type == "postgres":
                    upsert_via_merge(
                        self.etlo.new,
                        target_table,
                        df,
                        primary_keys,
                    )

                else:
                    # Upsert (insert with ON CONFLICT DO UPDATE) the data. This
                    # operation is specific to Postgres, but works with SQLite
                    # as well
                    # Finalize the DataFrame for the database
                    df = finalize_df_for_database(df)

                    upsert_stmt = insert(target_table).values(
                        # Use all columns in df
                        **{x: bindparam(x) for x in df.columns},
                    )

                    upsert_stmt = upsert_stmt.on_conflict_do_update(
                        index_elements=primary_keys,
                        # Set all columns except the primary keys
                        set_={
                            x: bindparam(x) for x in df.columns if x not in primary_keys
                        },
                    )
                    with self.etlo.new.engine.connect() as conn:
                        conn.execute(upsert_stmt, df.to_dict("records"))
                        conn.commit()

            except Exception as exc:
                # If ignore_errors is specified, proceed with the *slow*
                # row-by-row insert (ONLY) (after notifying user)
                # This allows rejecting specific records on failure
                if self.ignore_errors:
                    print(
                        f"Bulk UPSERT failed with\n\n{exc}\n\nProceeding with much slower row-by-row INSERT (ONLY)...",
                    )

                    ignore_count = 0
                    insert_stmt = insert(target_table).values(
                        # Use all columns in df
                        **{x: bindparam(x) for x in df.columns},
                    )
                    for row in df.to_dict("records"):
                        try:
                            with self.etlo.new.engine.connect() as conn:
                                conn.execute(insert_stmt, row)
                                conn.commit()
                        except:
                            ignore_count += 1

                    print(
                        f"Row-by-row insertion successful! {ignore_count} of {len(df)} records ignored.",
                    )

                else:
                    # Raise the original error after notifying user that
                    # specifying ignore_errors may be able to bypass the
                    # issue
                    print(
                        "The following error was raised during bulk UPSERT (setting ignore_errors=True may be able to load partial data):",
                    )
                    raise

        except:
            raise

        else:
            self.determine_completed_pages()

    def convert_household_from_json(self):
        """
        For each account, convert `app_householdmembers.household_info` from
        JSON into the new field-separated `birthdate`, `full_name`, and
        `identification_path`.

        """

        print("FINISH CONVERTING HOUSEHOLDMEMBERS")
