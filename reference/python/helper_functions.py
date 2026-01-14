import json
import re
from pathlib import Path
from typing import Union
from uuid import uuid1

import coftc_cred_man as crd
import numpy as np
import pandas as pd
from sqlalchemy import (
    URL,
    Column,
    MetaData,
    Table,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql.json import JSON, JSONB
from sqlalchemy.engine.base import Engine

# Use Postgres-specific insert
from sqlalchemy.sql.selectable import Select


class DBMetadata:
    def __init__(
        self,
        db_profile: str,
        tables_to_load: Union[list, tuple] = None,
    ):
        """
        Initialize the class to store SQLAlchemy parameters and metadata

        Parameters
        ----------
        db_profile : str
            Profile name for the database. The profile will be attempt to be
            loaded from coftc-cred-man and must contain the necessary parameters
            for connectivity to the database. If the profile can't be found, it
            will be treated as a path to a SQLite database.
        tables_to_load : Union[list, tuple], optional
            A subset of table names to load into the metadata reflection. This
            is useful for databases with many tables, where only a small subset
            is needed. The default is None, designating that all tables should
            be reflected.

        Returns
        -------
        None

        """

        # Define attributes
        self._tables_to_load = tables_to_load
        self.db_profile = db_profile

        # Determine if the profile is a database connection
        try:
            cred = crd.Cred(self.db_profile)
        except AttributeError:
            # Profile cannot be found; attempt to use db_profile as a path
            check_path = Path(self.db_profile)

            # If path exists and is a file, use the SQLite connection
            if check_path.exists() and check_path.is_file():
                # SQLite requires no user, just the path; store the path as the
                # credentials
                self.cred = check_path
                self.db_type = "sqlite"

                # Construct the SQLite connection string
                self.connection_url = URL.create(
                    "sqlite+pysqlite",
                    database=str(self.db_profile),
                )

            else:
                raise ImportError(
                    f"{self.db_profile} is not a valid database profile or SQLite path"
                )

        else:
            # Save the credentials
            self.cred = cred

            # The supported (non-SQLite) database types are deduced as follows:
            # - Oracle must have the 'driver' config key == 'oracle'
            # - SQL Server must contain 'SQL Server' in the 'driver' config key
            # - Postgres is the fallback
            if "driver" in cred.config:
                if cred.config["driver"].lower() == "oracle":
                    # Construct the Oracle connection string
                    self.db_type = "oracle"

                    # If the TNS string exists in the profile, use it; else, use
                    # parameters from separate keys
                    if "tns" in cred.config:
                        tns_host, tns_port, tns_service_name = re.match(
                            r"(\S+?)\:(\d+)\/(\S+)", cred.config["tns"]
                        ).groups()
                        self.connection_url = URL.create(
                            "oracle+oracledb",
                            username=cred.config["user"],
                            password=cred.password(),
                            host=tns_host,
                            port=tns_port,
                            query={"service_name": tns_service_name},
                        )

                    else:
                        self.connection_url = URL.create(
                            "oracle+oracledb",
                            username=cred.config["user"],
                            password=cred.password(),
                            host=cred.config["server"],
                            port=1521,
                            database=cred.config["hostname"],
                        )

                elif "sql server" in cred.config["driver"].lower():
                    self.db_type = "sql_server"

                    # Construct the SQL Server connection string
                    self.connection_url = URL.create(
                        "mssql+pyodbc",
                        host=cred.config["server"],
                        database=cred.config["hostname"],
                        # Take the ODBC driver text without any brackets
                        query={"driver": re.sub(r"{|}", "", cred.config["driver"])},
                    )

                else:
                    raise TypeError(
                        "Database type not recognized (SQL Server or Oracle were expected by 'driver')"
                    )

            else:
                self.db_type = "postgres"

                # Construct the Postgres connection string
                self.connection_url = URL.create(
                    "postgresql+psycopg",
                    username=cred.config["user"],
                    password=cred.password(),
                    host=cred.config["host"],
                    port=5432,
                    database=cred.config["db"],
                )

        # Connect to the database
        self.connect()

    def connect(self):
        """Connect to the database."""
        try:
            # Define the database engine
            self.engine = create_engine(self.connection_url)

            # Attempt to connect (load the metadata reflection)
            self.metadata = MetaData()

            # Only load the list of tables, if specified
            if isinstance(self._tables_to_load, (list, tuple)):
                self.metadata.reflect(
                    bind=self.engine,
                    # Some databases require a schema be defined
                    schema=self.cred.config["default_schema"]
                    if self.db_type != "sqlite" and "default_schema" in self.cred.config
                    else None,
                    # Only load the tables specified here. Note that, regardless
                    # of Oracle's default, use all-lowercase here to be treated
                    # as case-insensitive
                    only=self._tables_to_load,
                )
            else:
                self.metadata.reflect(
                    bind=self.engine,
                    # Some databases require a schema be defined
                    schema=self.cred.config["default_schema"]
                    if self.db_type != "sqlite" and "default_schema" in self.cred.config
                    else None,
                )

        except Exception as exc:
            raise Exception(
                f"Database connection to {self.db_profile} failed:\n{exc}"
            ) from exc

    def reconnect(self):
        """Reconnect to the database (e.g. to fix a stale connection)."""

        try:
            self.cleanup()
        except:
            pass
        self.connect()

    def cleanup(self):
        """
        Clean up the database connections.

        Note that this isn't strictly necessary, as garbage collection will take
        care of this for us.

        """

        self.engine.dispose()


class FieldMapping:
    def __init__(
        self,
        mappings: Union[list, tuple] = None,
    ):
        """
        Map fields from source to target.

        Parameters
        ----------
        mappings : Union[list, tuple], optional
            List of dictionaries of field mappings, available here as a
            convenience (the list will be fed through the same functions as
            individual-creation). Each dictionary must include these keys:
            'source_field', 'target_field'. 'target_type' is an additional
            (optional) key.

        Returns
        -------
        None

        """

        self.__source_fields = []
        self.__source_values = []
        self.__target_fields = []
        self.__target_types = []
        self.__indices = {}

        self.__mappings = mappings
        self.__import_mappings()

    def __import_mappings(self):
        """Import the initial mappings, if applicable."""

        if self.__mappings is not None:
            self.bulk_add(self.__mappings)

        # Delete the initial mappings
        del self.__mappings

    def _run_checks(self):
        """Run checks on data completeness."""

        # Ensure if any target_types exists, all are defined
        if self.__target_types:
            if len(self.__target_types) != len(self.__target_fields):
                raise TypeError(
                    "target_types must have a value for each target_field, or no values at all."
                )

    @property
    def source_fields(self):
        """
        Display the source_fields as an empty dictionary (relative to themselves).

        This is read-only because no setter is defined.

        """
        return {key: "" for key in self.__source_fields if key is not None}

    @property
    def source_values(self):
        """
        Return the source_values as a dictionary relative to source_fields.

        This is read-only because no setter is defined.

        """
        return {
            key: val
            for key, val in zip(self.__source_fields, self.__source_values)
            if key is not None
        }

    @property
    def target_fields(self):
        """
        Return the target_fields as a dictionary relative to source_fields.

        This is read-only because no setter is defined.

        """
        return {
            key: val
            for key, val in zip(self.__source_fields, self.__target_fields)
            if key is not None
        }

    @property
    def target_types(self):
        """
        Display the target_types as a dinctionary relative to source_fields.

        This is read-only because no setter is defined.

        """
        return {
            key: val
            for key, val in zip(self.__source_fields, self.__target_types)
            if key is not None
        }

    def bulk_add(
        self,
        ldict_input: Union[list, tuple],
    ):
        """
        Call add() in bulk. The difference between this and calling add() in a
        loop is that this waits until after the loop to run checks.

        Parameters
        ----------
        ldict_input : Union[list, tuple]
            The list/tuple of dictionaries to convert to field mapping. This
            must include 'source_field' and 'target_field' keys, plus an
            optional 'target_type' key.

        Returns
        -------
        None

        """

        for dct in ldict_input:
            self.add(**dct, run_checks=False)

        # Run checks after adding all values
        self._run_checks()

    def add(
        self,
        source_field: str,
        target_field: str,
        target_type: str = None,
        run_checks: bool = True,
    ):
        """
        Add a field mapping.

        Parameters
        ----------
        source_field : str
            The name of the source field.
        target_field : str
            The name of the target field.
        target_type : str, optional
            The datatype of the target field, if different than the source. The
            default is None, specifying that the source datatype will be used
            as the target datatype.
        run_checks : bool, optional
            Run checks on data completeness after adding values. The default is
            True.

        Returns
        -------
        None

        """

        # If source_field is not a string or is an empty string, set a
        # placeholder and define the value
        if isinstance(source_field, str) and source_field != "":
            # # If source_field is not a string, set a placeholder and define the value
            # if isinstance(source_field, str):
            source_name = source_field
            source_value = None
        else:
            source_name = str(uuid1()).replace("-", "")
            source_value = source_field

        # Ensure the field doesn't already exist
        if self.__indices.get(source_name) is not None:
            raise AttributeError(
                f"'{source_field}' already exists. Try update() instead."
            )

        # Store the next index for the field, for ease of lookup
        new_index = len(self.__source_fields)
        self.__indices.update({source_field: new_index})
        self.__source_fields = list(self.__source_fields[:new_index]) + [source_name]
        self.__source_values = list(self.__source_values[:new_index]) + [source_value]
        self.__target_fields = list(self.__target_fields[:new_index]) + [target_field]
        if target_type:
            self.__target_types = list(self.__target_types[:new_index]) + [target_type]

        if run_checks:
            self._run_checks()

    def remove(
        self,
        source_field: str,
    ):
        """
        Remove a field mapping.

        Parameters
        ----------
        source_field : str
            The name of the source field.

        Returns
        -------
        None

        """

        search_index = self.__indices.get(source_field)

        # Remove the values from their respective tuples. Note that this doesn't
        # delete the value, just replaces it with a None placeholder
        self.__source_fields = (
            list(self.__source_fields[:search_index])
            + [None]
            + list(self.__source_fields[search_index + 1 :])
        )
        self.__source_values = (
            list(self.__source_values[:search_index])
            + [None]
            + list(self.__source_values[search_index + 1 :])
        )
        self.__target_fields = (
            list(self.__target_fields[:search_index])
            + [None]
            + list(self.__target_fields[search_index + 1 :])
        )
        if hasattr(self, "__target_types"):
            self.__target_types = (
                list(self.__target_types[:search_index])
                + [None]
                + list(self.__target_types[search_index + 1 :])
            )

        # Remove the index (without reordering the 'indices' list)
        self.__indices[search_index] = None

    def update(
        self,
        source_field: str,
        target_field: str,
        target_type: str = None,
    ):
        """
        Add a field mapping.

        Parameters
        ----------
        source_field : str
            The name of the source field.
        target_field : str
            The name of the target field.
        target_type : str, optional
            The datatype of the target field, if different than the source. The
            default is None, specifying that the source datatype will be used
            as the target datatype.

        Returns
        -------
        None

        """

        self.remove(source_field)
        self.add(source_field, target_field, target_type)

    def get(
        self,
        source_field: str,
    ):
        """
        Get the field mapping, based on the source_field.

        Parameters
        ----------
        source_field : str
            The name of the source field.

        Returns
        -------
        dict
            Returns dictionary with keys 'target_name' and 'target_type'.

        """

        search_index = self.__indices.get(source_field)
        return_dict = {
            "target_name": self.__target_fields[search_index],
        }
        if self.__source_values[search_index]:
            return_dict.update(
                {
                    "source_value": self.__source_values[search_index],
                }
            )
        if hasattr(self, "__target_types"):
            return_dict.update(
                {
                    "target_type": self.__target_types[search_index],
                }
            )
        return return_dict

    def get_name(
        self,
        source_field: str,
    ):
        """
        Get the target_name, based on the source_field.

        Parameters
        ----------
        source_field : str
            The name of the source field.

        Returns
        -------
        str
            Returns corresponding target_name.

        """

        search_index = self.__indices.get(source_field)
        return self.__target_fields[search_index]

    def get_value(
        self,
        source_field: str,
    ):
        """
        Get the source_value, based on the source_field.

        Parameters
        ----------
        source_field : str
            The name of the source field.

        Returns
        -------
        Returns corresponding source_value.

        """

        search_index = self.__indices.get(source_field)
        return self.__source_values[search_index]

    def get_type(
        self,
        source_field: str,
    ):
        """
        Get the target_type, based on the source_field.

        Parameters
        ----------
        source_field : str
            The name of the source field.

        Returns
        -------
        str
            Returns corresponding target_type.

        """

        search_index = self.__indices.get(source_field)
        if hasattr(self, "__target_types"):
            return self.__target_types[search_index]


def upsert_via_merge(
    dbmetadata: DBMetadata,
    primary_table: Table,
    df_data: pd.DataFrame,
    key_fields: Union[list, tuple] = None,
):
    """
    Create an empty temporary table as an exact schema clone of a non-temp
    table. The temp table name is the name of the source table with '_temp'
    appended.

    Parameters
    ----------
    dbmetadata : DBMetadata
        The DBMetadata definition of the database to use for the creation.
    primary_table : Table
        The SQLAlchemy object of the table to clone as temporary.
    df_data : pd.DataFrame
        DataFrame with the data to be inserted into the temporary table.
    key_fields : Union[list, tuple], optional
        An explicit table-level UNIQUE constraint (e.g. spanning multiple
        colunmns); single-column constraints will be captured automatically
        from the non-temp table. The default is None, specifying no table-
        level constraints (beyond any created automatically).

    Returns
    -------
    None

    """

    if dbmetadata.db_type != "postgres":
        raise NotImplementedError(
            "The MERGE functionality used for the target table is currently only available for PostgreSQL."
        )

    # Create a new columns list with the source table stripped out
    columns = []
    for col in primary_table.columns:
        columns.append(
            Column(
                col.name,
                col.type,
                primary_key=col.primary_key,
                nullable=col.nullable,
                index=col.index,
                unique=col.unique,
                # Postgres uses server_default rather than autoincrement,
                # but there doesn't seem to be harm in having both
                autoincrement=col.autoincrement,
                server_default=col.server_default,
            )
        )

    # Create a UniqueConstraint only if key_fields exists and has multiple
    # values
    if key_fields and len(key_fields) > 1:
        temp_table = Table(
            f"{primary_table.name}_temp",
            dbmetadata.metadata,
            *columns,
            UniqueConstraint(*key_fields),
            prefixes=["TEMPORARY"],
        )
    else:
        temp_table = Table(
            f"{primary_table.name}_temp",
            dbmetadata.metadata,
            *columns,
            prefixes=["TEMPORARY"],
        )

    # Create temp_table *only* (temp_table should be the only additional
    # table anyway, but this ensures nothing else is touched)
    dbmetadata.metadata.create_all(
        dbmetadata.engine,
        tables=(temp_table,),
    )

    # Use the base (psycopg) DB API to COPY the df data to temp_table
    target_conn = dbmetadata.engine.connect().connection
    target_cursor = target_conn.cursor()

    # Copy the data. Rollback on error; else, commit
    try:
        with target_cursor.copy(
            'copy {nm} ("{fds}") from stdin'.format(
                nm=temp_table.name,
                fds='", "'.join(df_data.columns),
            )
        ) as cpy:
            for row in df_data.values.tolist():
                cpy.write_row(row)
    except:
        target_conn.rollback()
        raise
    else:
        target_conn.commit()

    # Close the DB API objects (this will just release the connection back
    # to SQLAlchemy)
    target_cursor.close()
    target_conn.close()

    # Upsert (via MERGE) the temp table into the primary table. This isn't
    # supported in SQLAlchemy 2.0, so use the plaintext SQL statement
    # functionality
    merge_stmt = text(
        """
            MERGE INTO {trgtbl} AS trg
            USING {tmptbl} AS tmp
            ON {keyfds}
            WHEN MATCHED THEN
            UPDATE SET {updfds}
            WHEN NOT MATCHED THEN
            INSERT ("{fds}")
            VALUES (tmp."{insfds}")
        """.format(
            trgtbl=primary_table.name,
            tmptbl=temp_table.name,
            keyfds=" AND ".join([f'trg."{x}"=tmp."{x}"' for x in key_fields]),
            fds='", "'.join(list(df_data.columns)),
            updfds=", ".join(
                [f'"{x}"=tmp."{x}"' for x in df_data.columns if x not in key_fields]
            ),
            insfds='", tmp."'.join(list(df_data.columns)),
        )
    )
    with dbmetadata.engine.connect() as conn:
        conn.execute(merge_stmt)
        conn.commit()


def process_data(
    db_query: Select,
    db_engine: Engine,
    field_mapping: FieldMapping = None,
):
    """
    Process the data into a pandas DataFrame object.

    Parameters
    ----------
    db_query : Select
        A SQLAlchemy SELECT statement to run against the specified engine.
    db_engine : Engine
        The database engine to use to run the db_query.
    field_mapping : FieldMapping, optional
        The field mapping from source (the fields in db_query) to the
        needed output, if applicable. The default is None, signifying that no
        changes need to be made.

    Returns
    -------
    DataFrame
        Returns a processed DataFrame of the selected data.

    """
    # Gather the data. dfiter returns an iterator of data chunks, which are
    # then looping over to return the full df
    dfiter = pd.read_sql(
        db_query,
        con=db_engine,
        # Chunk the result
        chunksize=100000,
        # Coerce datatypes to match target expectations (if exists). If the
        # target datatype is 'str', ignore it here; 'str' will coerce NULL
        # values to 'None' (a string), while the default will properly read NULL
        # as None (and bring string values in properly as well)
        dtype={
            key: val for key, val in field_mapping.target_types.items() if val != "str"
        },
    )

    for iteridx, itm in enumerate(dfiter):
        if iteridx == 0:
            df = itm
        else:
            # Concatenate itm with df
            if iteridx == 4:
                break
            df = pd.concat([df, itm], ignore_index=True)

    # Update all None values to '' for dtype 'str' (to follow Django guidelines
    # for using blank instead of NULL for CHAR fields)
    char_fields = [fd for fd, tp in field_mapping.target_types.items() if tp == "str"]
    for field in char_fields:
        df[field] = df[field].apply(lambda x: "" if x is None else x)

    # Rename the fields (if field_mapping exists)
    if field_mapping:
        df = df.rename(mapper=field_mapping.target_fields, axis=1)

    return df


def finalize_df_for_database(
    df_data: pd.DataFrame,
    db_fields: Union[list, tuple] = None,
):
    """
    Finalize the input DataFrame for insert into a database.

    Parameters
    ----------
    df_data : pd.DataFrame
        The input DataFrame to perform finalization on.
    db_fields : Union[list, tuple], optional
        Fields from the database that correspond to each column in the df.
        The default is None.

    Returns
    -------
    DataFrame
        Returns a finalized DataFrame.

    """
    # Stringify all dict fields (note that this is only available with Postgres
    # or SQLite as the source database, otherwise this will fail silently)
    if db_fields:
        # Verify the length of db_fields and df.columns is equal
        if len(db_fields) != len(df_data.columns):
            raise AttributeError(
                "db_fields must be the same length as the columns in the input DataFrame"
            )
        for nm, col in zip(df_data.columns, db_fields):
            if isinstance(col.type, (JSON, JSONB)) or isinstance(col.type, TEXT):
                df_data[nm] = df_data[nm].apply(json.dumps)

    # Replace all NaN and NaT with Python None
    df_data = df_data.replace({np.nan: None})

    return df_data
