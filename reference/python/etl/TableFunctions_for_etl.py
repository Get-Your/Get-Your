class TableFunctions:
    def __init__(self, etl_object):
        """Table-specific functions for the ETL process."""
        self.etlo = etl_object

    def mark_current_cycle_active(
        self,
        source_table: str,
        source_id_field: str,
        source_cycle_field: str,
        target_table: str,
    ):
        """
        Mark records in the specified table 'active' if the source data are in
        the current Budget Cycle.

        Parameters
        ----------
        source_table : str
            Name of the source table.
        source_id_field : str
            The ID field of the source table (which corresponds to the 'id'
            field of the target table).
        source_cycle_field : str
            The 'budget cycle number' field of the source table, to use for
            comparison to the bfocycle_budgetcycle target table.
        target_table : str
            Name of the target table.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and 'budget cycle' from the source table
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl}".format(
                fds=", ".join([source_id_field, source_cycle_field]),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Get the current budget cycle value, as the first value of the
            # first row
            current_cycle = self.etlo._execute_query(
                self.etlo.conn_dev,
                cursor_ftn_dev,
                "select id from bfocycle_budgetcycle where is_current=true",
            )[0][0]
            try:
                for itmid, itmcycle in db_out:
                    # This script's default for is_active is False, so only need
                    # to continue if it should be set to True
                    if itmcycle == current_cycle:
                        self.etlo._execute_query(
                            self.etlo.conn_dev,
                            cursor_ftn_dev,
                            "update public.{tbl} set is_active=%s where id=%s".format(
                                tbl=target_table,
                            ),
                            query_values=[(True, itmid)],
                            # Defer committing until the loop is complete
                        )
            except:
                self.etlo.conn_dev.rollback()
                raise
            else:
                self.etlo.conn_dev.commit()

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def set_primary_objective(
        self,
        source_table: str,
        source_primary_objective_id_field: str,
        target_table: str,
    ):
        """
        Mark records in the specified table 'primary' for the specified 'primary
        objective' field in source.

        Parameters
        ----------
        source_table : str
            Name of the source table.
        source_primary_objective_id_field : str
            The ID field of each Primary Objective in the source table.
        target_table : str
            Name of the target table.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather all legacy 'primary objective' IDs
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select distinct {fd} from {sch}.{tbl} where {fd} is not null".format(
                fd=source_primary_objective_id_field,
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            try:
                # Set primary objective IDs and add to WHERE clause in UPDATE
                primary_objective_ids = [str(x[0]) for x in db_out]
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "update public.{tbl} set is_primary=true where id in ({vls})".format(
                        tbl=target_table, vls=", ".join(primary_objective_ids)
                    ),
                    do_commit=True,
                )
            except:
                self.etlo.conn_dev.rollback()
                raise
        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def fill_values_with_user_lookup(
        self,
        source_table: str,
        source_id_field: str,
        source_user_field: str,
        target_table: str,
        target_user_field: str,
        is_nullable: bool = False,
    ):
        """
        Fill records in the specified table with the user lookup from the
        source.

        Parameters
        ----------
        source_table : str
            Name of the source table.
        source_id_field : str
            The ID field of the source table (which corresponds to the 'id'
            field of the target table).
        source_user_field : str
            The 'user' field of the source table. This should be a field of
            user ID strings.
        target_table : str
            Name of the target table.
        target_user_field : str
            The user-lookup field of the target table.
        is_nullable : bool, optional
            Parameter defining if the user_id field is nullable. If the field is
            nullable, a warning will be given for non-matching users, rather
            than an exception. The default is False.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and user lookup values
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl}".format(
                fds=", ".join([source_id_field, source_user_field]),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Look up each user in new BART. Use the 'new BART user suffix' that
            # was used for insert

            # Create lookup list as (legacy value, new value) from the distinct
            # (set) users in db_out
            user_ids_lookup = [
                (y, f"{y}{self.etlo.newbart_user_suffix}".lower())
                for y in set([x[1] for x in db_out])
                if y is not None
            ]
            user_ids_return = self.etlo._execute_query(
                self.etlo.conn_dev,
                cursor_ftn_dev,
                "select email, id from users_user where email in ('{eml}')".format(
                    eml="', '".join([x[1] for x in user_ids_lookup])
                ),
            )

            # Combine new BART user ID with legacy BART user name

            # If user_id field is nullable, keep a list of missing users to warn
            # at the end of the function
            if is_nullable:
                missing_users = []

            # Note user_ids_return and user_ids_lookup must be combined
            # element-by-element due to differences between the users table and
            # values in `source_user_field`
            name_userid_link = []
            for nm, eml in user_ids_lookup:
                try:
                    id_val = next(x[1] for x in user_ids_return if x[0] == eml)
                except StopIteration as excp:
                    # If a user is missing: if user_id is not nullable,
                    # recommend to running create_users() then pick back up
                    # filling tables with the current `target_table`; else, add
                    # the user to a missing_users list to warn about and skip it
                    if is_nullable:
                        missing_users.append(eml)
                    else:
                        raise StopIteration(
                            f"User(s) are missing from the new BART 'users' table; fill aborting.\n\nTo resolve, try running self.create_users() then continue filling tables with self.fill_all_tables(starting_target_table='{target_table}', ...)"
                        ) from excp
                else:
                    name_userid_link.append((nm, id_val))

            # Combine new BART offers_offer ID with new BART user ID

            id_userid_link = [
                (y[0], next(iter(x[1] for x in name_userid_link if x[0] == y[1]), None))
                for y in db_out
            ]

            # Add the ID/UserID match to a temp table and merge it with the
            # target table

            # Use the datatype of the first id in id_userid_link to determine
            # whether the temp table should have a string or int 'id' field
            if isinstance(id_userid_link[0][0], str):
                cursor_ftn_dev.execute(
                    "create temp table user_link (id varchar(100), user_id int8) on commit drop"
                )
            else:
                cursor_ftn_dev.execute(
                    "create temp table user_link (id int8, user_id int8) on commit drop"
                )

            with cursor_ftn_dev.copy("copy user_link (id, user_id) from stdin") as cpy:
                for row in id_userid_link:
                    cpy.write_row(row)

            try:
                cursor_ftn_dev.execute(
                    "merge into public.{tbl} as trg using user_link as src on trg.id=src.id when matched then update set {fd}=src.user_id".format(
                        tbl=target_table,
                        fd=target_user_field,
                    )
                )
            except:
                self.etlo.conn_dev.rollback()
                raise
            else:
                self.etlo.conn_dev.commit()

            # Warn of any missing users (if applicable)
            if is_nullable:
                warn(
                    "The following users are not in the 'users_user' table and were therefore skipped:\n{}".format(
                        "\n".join(missing_users),
                    )
                )

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def fill_related_offer_values(
        self,
        source_table: str,
        source_id_field: str,
        source_related_offer_field: str,
        target_table: str,
        target_related_offer_field: str,
    ):
        """
        Fill records in the specified table with the user lookup from the
        source.

        Parameters
        ----------
        source_table : str
            Name of the source table.
        source_id_field : str
            The ID field of the source table (which corresponds to the 'id'
            field of the target table).
        source_related_offer_field : str
            The 'related offer' linkage field of the source table.
        target_table : str
            Name of the target table.
        target_related_offer_field : str
            The 'related offer' linkage field of the target table.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and the related offer from the source table
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl}".format(
                # Note the field order; this matches the order of '%s' in the
                # update below
                fds=", ".join([source_related_offer_field, source_id_field]),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Limit db_out to nonzero, non-null values (zero===null in the
            # context of lookups, and all current values are null and therefore
            # don't need to be updated)
            db_out = [(x[0], x[1]) for x in db_out if x[0] is not None and x[0] > 0]

            try:
                # Update the target field with the source related_offer_field ID
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "update public.{tbl} set {fd}=%s where id=%s".format(
                        tbl=target_table,
                        fd=target_related_offer_field,
                    ),
                    query_values=db_out,
                    do_commit=True,
                )
            except:
                self.etlo.conn_dev.rollback()
                raise

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def fill_budget_cycles(self):
        """
        Fill bfocycle_budgetcycle and bfocycle_budgetcycleyear.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        # Define the source table
        source_table = "BudgetCycle"
        source_fields = [
            "intBudgetCycleNbr",
            "'FALSE'",
            "strYrOne",
            "strYrTwo",
            "intBudgetCycleNbr",
        ]

        # Define the target in the same order as source, as (table name, field
        # name)
        target_table = [
            ("bfocycle_budgetcycle", "id"),
            ("bfocycle_budgetcycle", "is_current"),
            ("bfocycle_budgetcycleyear", "year"),
            ("bfocycle_budgetcycleyear", "year"),
            ("bfocycle_budgetcycleyear", "budget_cycle_id"),
        ]

        # Define the cursors
        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Pull the data from the source table. This will also attempt to
        # auto-detect and convert Boolean values
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl} where intBudgetCycleNbr>0".format(
                fds=", ".join(source_fields),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Define binary lists for the 'budget cycle' and 'budget cycle year'
            # tables
            cycle_table_bin = [x[0] == "bfocycle_budgetcycle" for x in target_table]
            year_table_bin = [x[0] == "bfocycle_budgetcycleyear" for x in target_table]

            try:
                # Insert the data into bfocycle_budgetcycle. Do nothing for any
                # record that already exists
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "insert into public.{tbl} ({fds}) values ({plc}) on conflict (id) do nothing".format(
                        tbl="bfocycle_budgetcycle",
                        fds=", ".join(
                            [
                                x[1]
                                for idx, x in enumerate(target_table)
                                if cycle_table_bin[idx]
                            ]
                        ),
                        plc=", ".join(["%s"] * sum(cycle_table_bin)),
                    ),
                    query_values=[
                        [x for idx, x in enumerate(y) if cycle_table_bin[idx]]
                        for y in db_out
                    ],
                    do_commit=True,
                )

                # Insert into bfocycle_budgetcycleyear. db_out will need to be split
                # to create a new record for each year
                db_out_year = [
                    [x for idx, x in enumerate(y) if year_table_bin[idx]]
                    for y in db_out
                ]

                # Parse each year into its own element
                db_out_parsed = [(x[0], x[2]) for x in db_out_year] + [
                    (x[1], x[2]) for x in db_out_year
                ]

                # Remove any duplicates and sort by cycle then year
                db_out_parsed = list(set(db_out_parsed))
                db_out_parsed.sort(key=lambda x: (x[1], x[0]))

                # Insert the data. Do nothing for any record that already exists
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "insert into public.{tbl} ({fds}) values ({plc}) on conflict (year, budget_cycle_id) do nothing".format(
                        tbl="bfocycle_budgetcycleyear",
                        fds=", ".join(["year", "budget_cycle_id"]),
                        plc=", ".join(["%s"] * 2),
                    ),
                    query_values=db_out_parsed,
                    do_commit=True,
                )

                # Set is_current=True for the latest budget cycle
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "update public.{tbl} set is_current=true where id=(select max(id) from public.{tbl})".format(
                        tbl="bfocycle_budgetcycle",
                    ),
                    do_commit=True,
                )

            except:
                # Rollback on error (then raise exception)
                self.etlo.conn_dev.rollback()
                raise

        # Attempt to close each cursor (fail silently on error)
        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def set_offer_bu_in_offerfunding(self):
        """
        Set offer_bu_id into offers_offerfunding using
        SELECT intOfferBUID FROM OfferBU WHERE intOfferID = ? and strBU = ?

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        cursor_ftn_dev = (
            self.etlo.conn_dev.cursor()
        )  # use this one to insert into new DB
        cursor_ftn_prod = (
            self.etlo.conn_prod.cursor()
        )  # use this one to query the old DB

        #
        old_offerbuid_offerId_and_buid = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select intOfferBUID, intOfferID, strBU from {sch}.{tbl}".format(
                sch=self.etlo.prod.cred.config["default_schema"], tbl="OfferBU"
            ),
        )

        # iterate over the old table values, updating the new table for each row
        # UPDATE budget_fundingsource SET offer_bu_id = ? WHERE offer_id = ? AND bu_id = ?

    def fill_rating_rater_name(self):
        """
        Fill the ``rater_name`` field in ratings_rating, but only if the user_id
        field is null.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        source_table = "Ratings"
        source_id_field = "intRatingID"
        source_user_field = "strEmpID"
        target_table = "ratings_rating"
        target_rater_name_field = "rater_name"

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and the related offer from the source table
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl}".format(
                # Note the field order; this matches the order of '%s' in the
                # update below
                fds=", ".join([source_user_field, source_id_field]),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            try:
                # Update the target field with the source user_field string iff
                # target user_id field is null
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "update public.{tbl} set {fd}=%s where user_id is null and id=%s".format(
                        tbl=target_table,
                        fd=target_rater_name_field,
                    ),
                    query_values=db_out,
                    do_commit=True,
                )
            except:
                self.etlo.conn_dev.rollback()
                raise

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def fill_vacancyfactors(self):
        """
        Fill the 'vacancy_factors' M2M relation in PSC > ForecastState from the
        comma-delimited-number field in the legacy 'PSCForecastStates'.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        source_table = "PSCForecastStates"
        source_id_field = "intStateID"
        source_vf_field = "strVacancyFactorsPerYear"
        source_bfo_cycle_field = "p.intBudgetCycleNbr"
        # Gather BFO year in the same format as the vacancy factors
        source_bfo_year_field = "concat(strYrOne, ',', strYrTwo)"

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and the related offer from the source table
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from dbo.PscForecastStates p left join dbo.BudgetCycle b on p.intBudgetCycleNbr=b.intBudgetCycleNbr".format(
                # Note the field order; this matches the order of '%s' in the
                # update below
                fds=", ".join(
                    [
                        source_bfo_cycle_field,
                        source_bfo_year_field,
                        source_vf_field,
                        source_id_field,
                    ]
                ),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Extract all vacancy factors and align them with relevant data
            parsed_data = []
            for cycleitm, yritm, vfitm, iditm in db_out:
                # No need to process if vfitm is None
                if vfitm is None:
                    continue

                # Extract the corresponding year and vacancy factor
                parsed_data.extend(
                    [
                        (cycleitm, int(y), float(v), iditm)
                        for y, v in zip(yritm.split(","), vfitm.split(","))
                    ]
                )

            # Gather the ID for each year and replace the value in parsed_data
            year_lookup = self.etlo._execute_query(
                self.etlo.conn_dev,
                cursor_ftn_dev,
                "select {fds} from public.{tbl} where year in ({vls})".format(
                    # Note the field order; this matches the order of '%s' in the
                    # update below
                    fds=", ".join(["year", "id"]),
                    tbl="bfocycle_budgetcycleyear",
                    vls=", ".join(set([str(x[1]) for x in parsed_data])),
                ),
            )
            parsed_data = [
                (x[0], next(y[1] for y in year_lookup if y[0] == x[1]), x[2], x[3])
                for x in parsed_data
            ]

            # Insert the parsed data into the relevant tables
            try:
                for cycleitm, yriditm, vfitm, iditm in parsed_data:
                    # Insert the vacancy factor itself into psc_vacancyfactor
                    cursor_ftn_dev.execute(
                        "insert into public.{tbl} ({fds}) values ({plc}) returning id".format(
                            tbl="psc_vacancyfactor",
                            fds=", ".join(
                                [
                                    "budget_cycle_id",
                                    "year_id",
                                    "value",
                                ]
                            ),
                            plc=", ".join(["%s"] * 3),
                        ),
                        [cycleitm, yriditm, vfitm],
                    )
                    vacancyfactor_id = cursor_ftn_dev.fetchall()[0][0]

                    # Insert the vacancyfactor_id and iditm into the
                    # psc_forecaststate_vacancy_factors linkage table (this table
                    # is accessed via the ForecastState.vacancy_factors M2M field)
                    cursor_ftn_dev.execute(
                        "insert into public.{tbl} ({fds}) values ({plc})".format(
                            tbl="psc_forecaststate_vacancy_factors",
                            fds=", ".join(["vacancyfactor_id", "forecaststate_id"]),
                            plc=", ".join(["%s"] * 2),
                        ),
                        [vacancyfactor_id, iditm],
                    )

            except:
                self.etlo.conn_dev.rollback()
                raise

            else:
                self.etlo.conn_dev.commit()

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def add_budget_cycle_to_db_out(
        self,
        db_in: list,
        fields: Union[list, tuple],
        target_year_field: str,
    ):
        """
        Add the relevant budget cycle to the output from the source table.

        Note that this expects the target field to be ``budget_cycle_id``.

        Parameters
        ----------
        db_in : list
            The output from the source database.
        fields : Union[list, tuple]
            The field names that correspond to db_out (in the same order) in the
            *target* database.
        target_year_field : str
            The reference 'year' field in the target table.

        Returns
        -------
        tuple or None
            Returns a tuple of db_out (with added budget_cycle_id), fields (with
            added budget_cycle_id) or None, if budget_cycle_lookup can't be
            found.

        """
        # Define the index in fields of target_year_field
        year_index = fields.index(target_year_field)

        # Define the source table
        source_table = "bfocycle_budgetcycleyear"

        # Define the cursors
        cursor_ftn_dev = self.etlo.conn_dev.cursor()

        # Pull the data from the source table. This will also attempt to
        # auto-detect and convert Boolean values
        budget_cycle_lookup = self.etlo._execute_query(
            self.etlo.conn_dev,
            cursor_ftn_dev,
            """select "year", max(budget_cycle_id) as budget_cycle_id from public.{tbl} group by "year" """.format(
                tbl=source_table,
            ),
        )

        if len(budget_cycle_lookup) > 0:
            # Append budget_cycle_id to fields
            fields.append("budget_cycle_id")

            # Append the budget cycle id to each element of db_in (None if not
            # found). Note that the order of budget_cycle_lookup is
            # (year, budget_cycle_id)
            db_in = [
                tuple(
                    list(x)
                    + [
                        next(
                            iter(
                                id
                                for yr, id in budget_cycle_lookup
                                if yr == int(x[year_index])
                            ),
                            None,
                        )
                    ]
                )
                for x in db_in
            ]

            return (db_in, fields)

        # Attempt to close each cursor (fail silently on error)
        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def add_budget_cycle_to_df(
        self,
        dbmetadata: DBMetadata,
        df_in: pd.DataFrame,
        target_year_field: str,
    ):
        """
        Add the relevant budget cycle to the input DataFrame.

        Note that this expects the target field to be ``budget_cycle_id``.

        Parameters
        ----------
        dbmetadata : DBMetadata
            The SQLAlchemy object for the database to use.
        df_in : pd.DataFrame
            The input DataFrame to add budget cycle to.
        target_year_field : str
            The reference 'year' field in the input dataframe.

        Returns
        -------
        pd.DataFrame
            Returns the input DataFrame with budget_cycle_id added.

        """
        # Determine if target_year_field is a string or int column (if pandas
        # converted the target_year_field column to object or category, it's
        # string)
        df_obj = df_in.select_dtypes("object", "category")
        if target_year_field in df_obj.columns:
            year_dtype = "str"
        else:
            year_dtype = "int"

        # Gather the BudgetCycleYear table to get BudgetCycle data
        cycle_year_table = Table(
            "bfocycle_budgetcycleyear",
            dbmetadata.metadata,
            autoload_with=dbmetadata.engine,
        )
        # Define field mapping for the linkage and id fields. Use Python
        # datatypes that correspond to the target database, and name the 'year'
        # field to be the same as target_year_field input.
        cycle_year_mapping = FieldMapping(
            mappings=[
                {
                    "source_field": "year",
                    "target_field": target_year_field,
                    "target_type": year_dtype,
                },
                {
                    "source_field": "budget_cycle_id",
                    "target_field": "budget_cycle_id",
                    "target_type": "int",
                },
            ]
        )
        # Because 'year' isn't unique to the data (somehow), we'll use a max()
        # for budget_cycle_id and id while grouping by 'year'
        stmt = (
            select(
                func.max(cycle_year_table.c.budget_cycle_id).label("budget_cycle_id"),
                cycle_year_table.c.year,
            )
            .group_by(cycle_year_table.c.year)
            .order_by(cycle_year_table.c.year)
        )

        # Pull the data into a DataFrame and process it
        df_link = process_data(stmt, dbmetadata.engine, cycle_year_mapping)

        # df_in may contain 'year' values outside of BudgetCycleYear, which means
        # there will be NaN values when merged. As queried, the default NumPy
        # int64 datatypes can't store NaN values, so they would be converted to
        # float, which wouldn't be allowed in the database. To work around this,
        # convert year_id and budget_cycle_id to nullable-integer types (see
        # https://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#support-for-integer-na
        # for more details on NumPy not supporting NaN integers)
        convert_dict = {x: pd.Int64Dtype() for x in ["budget_cycle_id"]}
        df_link = df_link.astype(convert_dict)

        # Join the linkage table to the primary DataFrame on target_year_field
        df_in = df_in.merge(
            df_link,
            how="left",
            on=target_year_field,
        )

        return df_in

    def fill_account_owners(self):
        """
        Fill the ``name_id`` and ``comment`` fields in
        revenue_accountowner. If the specified 'name' value has no
        match in users_user, place the value in 'comment'.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        # First, load the source and target tables from metadata reflections
        source_table = Table(
            "AccountMaster",
            self.etlo.prod.metadata,
            autoload_with=self.etlo.prod.engine,
        )
        target_table = Table(
            "revenue_accountowner",
            self.etlo.dev.metadata,
            autoload_with=self.etlo.dev.engine,
        )

        # Note that this is basically the same strategy as
        # fill_values_with_user_lookup(), except this includes some additional
        # data and will insert any existing account owners into the target table

        # Define field mapping. Use Python datatypes that correspond to the
        # target database
        field_mapping = FieldMapping(
            mappings=[
                {
                    "source_field": "strAccountID",
                    "target_field": "account_id",
                    "target_type": "str",
                },
                {
                    "source_field": "strAcctOwner",
                    "target_field": "legacy_name",
                    "target_type": "str",
                },
                {
                    "source_field": "dtmUpdatedDate",
                    "target_field": "created_at",
                    "target_type": "str",
                },
                {
                    "source_field": "strUpdatedBy",
                    "target_field": "created_by",
                    "target_type": "str",
                },
            ]
        )
        stmt = select(
            *[source_table.c.get(x) for x in field_mapping.source_fields.keys()],
        )

        # Pull the data into a DataFrame and process it
        df_account = process_data(stmt, self.etlo.prod.engine, field_mapping)

        # Add the process records
        column_length = len(df_account)
        df_account = df_account.assign(
            is_active=column_length * [True],
            # 'modified' will be the same as 'created' for ETL purposes
            modified_at=df_account["created_at"],
            modified_by=df_account["created_by"],
        )

        if len(df_account) > 0:
            # Look up each user in new BART. Use the 'new BART user suffix' that
            # was used for insert

            # Define a lookup DataFrame with legacy_name from the distinct users
            # in df_account
            distinct_legacy_name = df_account["legacy_name"].unique()
            df_lookup = pd.DataFrame(
                data={
                    "legacy_name": distinct_legacy_name,
                },
            )

            # Define the new name with the standard coercion method (see
            # fill_values_with_user_lookup())
            df_lookup = df_lookup.assign(
                email=df_lookup[["legacy_name"]].map(
                    lambda x: f"{x}{self.etlo.newbart_user_suffix}".lower()
                ),
            )

            # Pull the user values and match the ID with the name
            user_table = Table(
                "users_user",
                self.etlo.dev.metadata,
                autoload_with=self.etlo.dev.engine,
            )
            stmt = select(user_table.c["id", "email"]).where(
                user_table.c.email.in_(list(df_lookup["email"])),
            )
            df_user = pd.read_sql(
                stmt,
                con=self.etlo.dev.engine,
            )

            # Join df_user onto df_lookup, using 'email' as the key
            df_lookup = df_lookup.merge(
                df_user,
                on="email",
            )

            # Add a record to df_lookup for legacy_name=='Not Budgeted'. This
            # will be used later to insert comment_id=1 into the target table
            # Note that 'Not Budgeted' is the only non-user 'account owner' from
            # the legacy table to be retained; the other value, 'NewFromJDE',
            # is implied by blank values
            comment_record = pd.DataFrame(
                {
                    "legacy_name": ["Not Budgeted"],
                    "email": [None],
                    "id": [None],
                }
            )
            df_lookup = pd.concat(
                [df_lookup, comment_record],
                ignore_index=True,
            )

            # Now join df_lookup onto df_account to match user_id with
            # account_id. The join key is 'legacy_name'
            # Use an inner join (the default) for this, so that only accounts
            # with matching legacy_name will be in the final df_to_insert
            df_to_insert = df_account.merge(
                df_lookup,
                on="legacy_name",
            )

            # Before continuing, find all users *not* included in df_to_insert.
            # This returns the unique legacy_name values that are not in
            # df_to_insert
            is_in_lookup = df_account["legacy_name"].isin(df_to_insert["legacy_name"])
            names_not_in_lookup = df_account[~is_in_lookup]["legacy_name"].unique()

            # 'NewFromJDE' and 'Not Budgeted' are expected; raise exception if
            # there are any other values
            missing_names = [
                x
                for x in names_not_in_lookup
                if x not in ("NewFromJDE", "Not Budgeted")
            ]
            if len(missing_names) > 0:
                raise AttributeError(
                    "fill_account_owners(): The following account_owners are not in the 'users_user' table and must be added before continuing:\n{}".format(
                        "\n".join(missing_names),
                    )
                )

            # Add comment_id=1 for all 'Not Budgeted' values
            df_to_insert = df_to_insert.assign(
                # comment_id==1 is the 'Not Budgeted' linkage, per revenue migrations
                comment_id=df_to_insert[["legacy_name"]].map(
                    lambda x: 1 if x == "Not Budgeted" else pd.NA
                )
            )

            # Remove legacy_name and email from df_to_insert and rename 'id' to
            # user_id. The resulting columns will be inserted into
            # revenue_accountowner
            del df_to_insert["legacy_name"]
            del df_to_insert["email"]
            df_to_insert = df_to_insert.rename({"id": "user_id"}, axis=1)

            # Finalize df_to_insert for database insert
            df_to_insert = finalize_df_for_database(df_to_insert)

            # Insert the values
            insert_stmt = insert(target_table).values(
                # Use all columns in df
                **{x: bindparam(x) for x in df_to_insert.columns}
            )
            with self.etlo.dev.engine.connect() as conn:
                conn.execute(insert_stmt, df_to_insert.to_dict("records"))
                conn.commit()

    def add_additional_records(
        self,
        target_table: str,
        records: Union[list, tuple],
    ):
        """
        Add additional record(s) to the specified table. This is generally for
        adding a 'zero' value to make FKs workable.

        Parameters
        ----------
        target_table : str
            Name of the target table.
        records : Union[list, tuple]
            A list/tuple where each element is a dictionary of values to insert
            into the table.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()

        for itm in records:
            fields = itm.keys()
            try:
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "insert into public.{tbl} ({fds}) values ({plc})".format(
                        tbl=target_table,
                        fds=", ".join(fields),
                        plc=", ".join(["%s"] * len(itm)),
                    ),
                    query_values=[[itm[x] for x in fields]],
                    # Commit each row
                    do_commit=True,
                )
            except:
                self.etlo.conn_dev.rollback()

        try:
            cursor_ftn_dev.close()
        except:
            pass

    def fill_revenue_account(self):
        """
        Fill revenue_accountfundingsource and revenue_revenue from their
        corresponding legacy tables.

        revenue_accountfundingsource needs to have duplicates removed from the
        legacy data; revenue_revenue needs to have its FK IDs updated to match.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        # First, load the source and target tables from metadata reflections
        source_linkage_table = Table(
            "AccountRevenueGroup",
            self.etlo.prod.metadata,
            autoload_with=self.etlo.prod.engine,
        )
        source_revenue_table = Table(
            "Revenue",
            self.etlo.prod.metadata,
            autoload_with=self.etlo.prod.engine,
        )
        target_linkage_table = Table(
            "revenue_accountfundingsource",
            self.etlo.dev.metadata,
            autoload_with=self.etlo.dev.engine,
        )
        target_revenue_table = Table(
            "revenue_revenue",
            self.etlo.dev.metadata,
            autoload_with=self.etlo.dev.engine,
        )

        # Define field mapping for the 'linkage' table. Use Python datatypes
        # that correspond to the target database
        linkage_field_mapping = FieldMapping(
            mappings=[
                {
                    "source_field": "intAcctRevGrpID",
                    "target_field": "id",
                    "target_type": "int",
                },
                {
                    "source_field": "strAccountID",
                    "target_field": "account_id",
                    "target_type": "str",
                },
                {
                    "source_field": "intFundingSourceID",
                    "target_field": "funding_source_id",
                    "target_type": "int",
                },
                {
                    "source_field": "dtmUpdatedDate",
                    "target_field": "created_at",
                    "target_type": "str",
                },
                {
                    "source_field": "strUpdatedBy",
                    "target_field": "created_by",
                    "target_type": "str",
                },
            ]
        )
        stmt = select(
            *[
                source_linkage_table.c.get(x)
                for x in linkage_field_mapping.source_fields.keys()
            ],
        )

        # Pull the data into a DataFrame and process it
        df_linkage = process_data(stmt, self.etlo.prod.engine, linkage_field_mapping)

        # Define field mapping for the 'revenue' table. Use Python datatypes
        # that correspond to the target database
        revenue_field_mapping = FieldMapping(
            mappings=[
                {
                    "source_field": "intRevenueID",
                    "target_field": "id",
                    "target_type": "int",
                },
                {
                    "source_field": "strLedgerYear",
                    "target_field": "ledger_year",
                    "target_type": "str",
                },
                # 'orig_arg_id' is a standin; the 'account_revenue_group_id'
                # field will be calculated below
                {
                    "source_field": "intAcctRevGrpID",
                    "target_field": "orig_arg_id",
                    "target_type": "int",
                },
                {
                    "source_field": "curAmount",
                    "target_field": "amount",
                    "target_type": "float",
                },
                {
                    "source_field": "strComments",
                    "target_field": "comment",
                    "target_type": "str",
                },
                {
                    "source_field": "dtmUpdatedDate",
                    "target_field": "created_at",
                    "target_type": "str",
                },
                {
                    "source_field": "strUpdatedBy",
                    "target_field": "created_by",
                    "target_type": "str",
                },
            ]
        )
        stmt = select(
            *[
                source_revenue_table.c.get(x)
                for x in revenue_field_mapping.source_fields.keys()
            ],
        )

        # Pull the data into a DataFrame and process it
        df_revenue = process_data(stmt, self.etlo.prod.engine, revenue_field_mapping)

        # Add process records
        column_length = len(df_revenue)
        df_revenue = df_revenue.assign(
            is_active=column_length * [True],
            # 'modified' will be the same as 'created' for ETL purposes
            modified_at=df_revenue["created_at"],
            modified_by=df_revenue["created_by"],
        )

        if len(df_linkage) > 0 and len(df_revenue) > 0:
            # Remove duplicates from df_linkage and amend the affected IDs in
            # df_revenue

            # Note the duplicate fields in df_linkage, using unique_fields (a
            # clone of the table constraint)
            unique_fields = ["funding_source_id", "account_id"]

            # Gather binary Series of 1) all records with duplicates and 2) just
            # the duplicates that will be removed
            all_duplicated_bin = df_linkage.duplicated(
                subset=unique_fields,
                keep=False,
            )
            # Everything not True below will be kept
            rows_to_remove_bin = df_linkage.duplicated(
                subset=unique_fields,
                keep="first",
            )

            # Compare the differences between 'all duplicated' and 'final' (with
            # all but one of each duplicate removed). The df indexes in
            # rows_to_keep will be those to be removed (because that's
            # where the two Series don't match)
            rows_to_keep = rows_to_remove_bin.compare(all_duplicated_bin)
            # Rows to keep are all indexes in rows_to_remove_bin
            rows_to_remove = rows_to_remove_bin[rows_to_remove_bin]

            # Document the id, account_id, and funding_source_id that will be
            # removed
            df_linkage_to_remove = df_linkage.iloc[rows_to_remove.index, :]
            id_conversion_df = pd.DataFrame()
            id_conversion_df = id_conversion_df.assign(
                orig_arg_id=df_linkage_to_remove["id"],
                account_id=df_linkage_to_remove["account_id"],
                funding_source_id=df_linkage_to_remove["funding_source_id"],
            )
            # Reset the index to avoid confusion (indexes aren't relevant for
            # the next step)
            id_conversion_df.reset_index(drop=True, inplace=True)

            # Find the 'new' IDs to use for each element in id_conversion_df.
            # This matches account_id and funding_source_id from
            # id_conversion_df to df_linkage_to_keep
            df_linkage_to_keep = df_linkage.iloc[rows_to_keep.index, :]
            id_conversion_df["new_arg_id"] = id_conversion_df.apply(
                lambda y: next(
                    iter(
                        x.id
                        for x in df_linkage_to_keep.itertuples()
                        if x.account_id == y["account_id"]
                        and x.funding_source_id == y["funding_source_id"]
                    )
                ),
                axis=1,
            )

            # Delete the intermediary columns from id_conversion_df
            del id_conversion_df["account_id"]
            del id_conversion_df["funding_source_id"]

            # Now that we have the ID mapping, remove duplicates from df_linkage
            df_linkage = df_linkage.drop_duplicates(
                subset=unique_fields,
                keep="first",
            )

            # The merge to df_revenue will create NaN values, which aren't
            # compatible with default NumPy integer types; to work around this,
            # convert new_id to nullable-integer types (see
            # https://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#support-for-integer-na
            # for more details on NumPy not supporting NaN integers)
            convert_dict = {"new_arg_id": pd.Int64Dtype()}
            id_conversion_df = id_conversion_df.astype(convert_dict)

            # Convert relevant df_revenue IDs to the new values

            # Merge id_conversion_df on orig_id
            df_revenue = df_revenue.merge(
                id_conversion_df,
                how="left",
                on="orig_arg_id",
            )
            # Combine new and orig IDs into an 'account_revenue_group_id' column
            # and delete the former two
            df_revenue["account_revenue_group_id"] = df_revenue.apply(
                lambda x: x["orig_arg_id"]
                if pd.isna(x["new_arg_id"])
                else x["new_arg_id"],
                axis=1,
            )
            del df_revenue["orig_arg_id"]
            del df_revenue["new_arg_id"]

            # Now find the NULL values in account_id (funding_source_id cannot
            # be NULL in the source table) in df_linkage, remove them from
            # df_linkage, and nullify the df_revenue IDs
            df_linkage_nulls = df_linkage[df_linkage["account_id"].isna()]

            # Nullify the matching IDs in df_revenue. Since there will be NaN
            # values, first convert account_revenue_group_id to nullable-integer
            # type (see
            # https://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#support-for-integer-na
            # for more details on NumPy not supporting NaN integers)
            convert_dict = {"account_revenue_group_id": pd.Int64Dtype()}
            df_revenue = df_revenue.astype(convert_dict)

            # Find arg IDs that correspond to the null linkage IDs, add the
            # funding_source_id to the 'comment' field (for posterity) and set
            # the IDs to NaN
            df_revenue_arg_nulls = df_revenue["account_revenue_group_id"].isin(
                df_linkage_nulls["id"]
            )
            df_revenue["comment"] = df_revenue.apply(
                lambda x: f"{x['comment']} (legacy funding_source_id == {df_linkage[df_linkage['id'] == x['account_revenue_group_id']]['funding_source_id'].iloc[0]})"
                if x["id"] in df_linkage_nulls["id"] and x["comment"] is not None
                else f"Legacy funding_source_id == {df_linkage[df_linkage['id'] == x['account_revenue_group_id']]['funding_source_id'].iloc[0]}"
                if x["id"] in df_linkage_nulls["id"]
                else x["comment"],
                axis=1,
            )
            df_revenue["account_revenue_group_id"] = df_revenue[
                "account_revenue_group_id"
            ].where(~df_revenue_arg_nulls, other=pd.NA)

            # Now remove the null elements from df_linkage
            df_linkage.drop(
                index=df_linkage_nulls.index,
                axis=1,
                inplace=True,
            )

            # Add budget_cycle_id to df_revenue
            df_revenue = self.add_budget_cycle_to_df(
                self.etlo.dev,
                df_revenue,
                "ledger_year",
            )

            # Replace all NaN and NaT in df_revenue with Python None
            df_revenue = df_revenue.replace({np.nan: None})

            # Insert the values into target_linkage_table (first)
            insert_stmt = insert(target_linkage_table).values(
                # Use all columns in df
                **{x: bindparam(x) for x in df_linkage.columns}
            )
            with self.etlo.dev.engine.connect() as conn:
                conn.execute(insert_stmt, df_linkage.to_dict("records"))
                conn.commit()

            # Insert the values into target_revenue_table
            insert_stmt = insert(target_revenue_table).values(
                # Use all columns in df
                **{x: bindparam(x) for x in df_revenue.columns}
            )
            with self.etlo.dev.engine.connect() as conn:
                conn.execute(insert_stmt, df_revenue.to_dict("records"))
                conn.commit()

    def fill_job_type_values(
        self,
        source_table: str,
        source_id_field: str,
        source_job_type_field: str,
        target_table: str,
        target_job_type_field: str,
    ):
        """
        Fill records in the specified table with the lookup from the
        source.

        Parameters
        ----------
        source_table : str
            Name of the source table.
        source_id_field : str
            The ID field of the source table (which corresponds to the 'id'
            field of the target table).
        source_job_type_field : str
            The 'job type' linkage field of the source table.
        target_table : str
            Name of the target table.
        target_job_type_field : str
            The 'job type' linkage field of the target table.

        Returns
        -------
        None

        """

        cursor_ftn_dev = self.etlo.conn_dev.cursor()
        cursor_ftn_prod = self.etlo.conn_prod.cursor()

        # Gather ID and the job type from the source table
        db_out = self.etlo._execute_query(
            self.etlo.conn_prod,
            cursor_ftn_prod,
            "select {fds} from {sch}.{tbl}".format(
                # Note the field order; this matches the order of '%s' in the
                # update below
                fds=", ".join([source_id_field, source_job_type_field]),
                sch=self.etlo.prod.cred.config["default_schema"],
                tbl=source_table,
            ),
        )

        if len(db_out) > 0:
            # Replace the second value with the ID lookup from JobTypes
            lookup_out = self.etlo._execute_query(
                self.etlo.conn_prod,
                cursor_ftn_prod,
                "select {fds} from {sch}.{tbl}".format(
                    # Note the field order; this matches the order of '%s' in the
                    # update below
                    fds=", ".join(["strJobType", "intJobTypeID"]),
                    sch=self.etlo.prod.cred.config["default_schema"],
                    tbl="JobTypes",
                ),
            )

            db_to_insert = []
            for itm in db_out:
                if itm[1] is None:
                    lookup_id = None
                else:
                    lookup_id = next(iter(x[1] for x in lookup_out if x[0] == itm[1]))
                db_to_insert.append((lookup_id, itm[0]))

            try:
                # Update the target field with the source job_type ID
                self.etlo._execute_query(
                    self.etlo.conn_dev,
                    cursor_ftn_dev,
                    "update public.{tbl} set {fd}=%s where id=%s".format(
                        tbl=target_table,
                        fd=target_job_type_field,
                    ),
                    query_values=db_to_insert,
                    do_commit=True,
                )
            except:
                self.etlo.conn_dev.rollback()
                raise

        try:
            cursor_ftn_dev.close()
        except:
            pass
        try:
            cursor_ftn_prod.close()
        except:
            pass

    def fill_revenueright(self):
        """
        Fill revenue_revenueright from legacy RevenueRights. This is a separate
        function in order to remove duplicate (account, user) values.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        # First, load the source and target tables from metadata reflections
        source_table = Table(
            "RevenueRights",
            self.etlo.prod.metadata,
            autoload_with=self.etlo.prod.engine,
        )
        target_table = Table(
            "revenue_revenueright",
            self.etlo.dev.metadata,
            autoload_with=self.etlo.dev.engine,
        )
        # Define field mapping for the target table. Use Python datatypes
        # that correspond to the target database
        field_mapping = FieldMapping(
            mappings=[
                {
                    "source_field": "intRevenueRightsID",
                    "target_field": "id",
                    "target_type": "int",
                },
                {
                    "source_field": "strAccountID",
                    "target_field": "account_id",
                    "target_type": "str",
                },
                # Use strEmpID to fill the user values
                {
                    "source_field": "strEmpID",
                    "target_field": "legacy_name",
                    "target_type": "str",
                },
                {
                    "source_field": "dtmUpdatedDate",
                    "target_field": "created_at",
                    "target_type": "str",
                },
                {
                    "source_field": "strUpdatedBy",
                    "target_field": "created_by",
                    "target_type": "str",
                },
            ]
        )
        stmt = select(
            *[
                func.lower(source_table.c.get(x)).label("strEmpID")
                if x == "strEmpID"
                else source_table.c.get(x)
                for x in field_mapping.source_fields.keys()
            ],
        )

        # Pull the data into a DataFrame and process it
        df = process_data(stmt, self.etlo.prod.engine, field_mapping)

        if len(df) > 0:
            # Look up each user in new BART. Use the 'new BART user suffix' that
            # was used for insert

            # Define a lookup DataFrame with legacy_name from the distinct users
            # in df_account
            distinct_legacy_name = df["legacy_name"].unique()
            df_lookup = pd.DataFrame(
                data={
                    "legacy_name": distinct_legacy_name,
                },
            )

            # Define the new name with the standard coercion method (see
            # fill_values_with_user_lookup())
            df_lookup = df_lookup.assign(
                email=df_lookup[["legacy_name"]].map(
                    lambda x: f"{x}{self.etlo.newbart_user_suffix}".lower()
                ),
            )

            # Pull the user values and match the ID with the name
            user_table = Table(
                "users_user",
                self.etlo.dev.metadata,
                autoload_with=self.etlo.dev.engine,
            )
            stmt = select(
                user_table.c.id.label("user_id"),
                user_table.c.email,
            ).where(
                user_table.c.email.in_(list(df_lookup["email"])),
            )
            df_user = pd.read_sql(
                stmt,
                con=self.etlo.dev.engine,
            )

            # Join df_user onto df_lookup, using 'email' as the key
            df_lookup = df_lookup.merge(
                df_user,
                on="email",
            )

            # Now join df_lookup onto df to match user_id with
            # account_id. The join key is 'legacy_name'
            # Use an inner join (the default) for this, so that only accounts
            # with matching legacy_name will be in the final df_to_insert
            df_to_insert = df.merge(
                df_lookup,
                on="legacy_name",
            )

            # Before continuing, find all users *not* included in df_to_insert.
            # This returns the unique legacy_name values that are not in
            # df_to_insert
            is_in_lookup = df["legacy_name"].isin(df_to_insert["legacy_name"])
            names_not_in_lookup = df[~is_in_lookup]["legacy_name"].unique()

            # Raise exception if there are any values
            if len(names_not_in_lookup) > 0:
                raise AttributeError(
                    "fill_revenueright(): The following 'revenue rights' users are not in the 'users_user' table and must be added before continuing:\n{}".format(
                        "\n".join(names_not_in_lookup),
                    )
                )

            # Remove duplicates of (account_id, user_id) from df
            unique_fields = ["account_id", "user_id"]
            df_to_insert = df_to_insert.drop_duplicates(
                subset=unique_fields,
            )

            # Remove legacy_name and email from df_to_insert. The resulting
            # columns will be inserted into revenue_revenueright
            del df_to_insert["legacy_name"]
            del df_to_insert["email"]

            # Finalize df_to_insert for database insert
            df_to_insert = finalize_df_for_database(df_to_insert)

            # Insert the values
            insert_stmt = insert(target_table).values(
                # Use all columns in df
                **{x: bindparam(x) for x in df_to_insert.columns}
            )
            with self.etlo.dev.engine.connect() as conn:
                conn.execute(insert_stmt, df_to_insert.to_dict("records"))
                conn.commit()
