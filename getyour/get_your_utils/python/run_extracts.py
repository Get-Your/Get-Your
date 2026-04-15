"""
Get-Your-utils consists of utility scripts for the Get-Your
application, used primarily by the City of Fort Collins.
Copyright (C) 2023

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

import os
import pendulum
import json
import psycopg2
import decimal
import re
from tomlkit import loads
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ClientAuthenticationError
from rich.progress import Progress
from typing import Union
import pandas as pd
from fnmatch import fnmatch

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import print

import ast
import warnings

from django.db.models import Count, Func, F, Value
from app import models
from app.models import IQProgramRD, IQProgram, User, HouseholdMembersHist
# import coftc_cred_man as crd
# import coftc_file_utils

# class GetFoco:
    
#     def __init__(
#         self,
#         output_file_dir,
#         **kwargs,
#         ):
#         """
#         Initialize the parameters needed for getfoco-admin actions.

#         Parameters
#         ----------
#         db_profile : STR, optional
#             The coftc-cred-man profile with the proper credentials for the
#             database connection. The default is 'getfoco_prod'.

#         Returns
#         -------
#         None.

#         """

#         db_profile = 'getfoco_prod' if not 'db_profile' in kwargs.keys() else kwargs['db_profile']
        
#         # Connect to the Azure Postgres database behind the Django app
#         self.cred = crd.Cred(db_profile)
#         self.output_file_dir = Path(output_file_dir)
        
#         self.host = self.cred.config['host']
#         self.user = self.cred.config['user']
#         self.dbname = self.cred.config['db']
        
#         self._connect()

#         # Define the standard query framework
#         # This uses the mailing address for all extracts
#         self.select_framework = """
#             select {fields} from public.app_user u
#             left join (select * from public.app_address ia 
#                 inner join public.app_addressrd iar on iar.id=ia.mailing_address_id) am on am.user_id=u.id
#             left join public.app_household h on h.user_id=u.id
#             left join public.app_householdmembers m on m.user_id=u.id
#             {additionalJoin}

#             {wherePlaceholder}
            
#             order by u.id asc
#             """
            
#         # Formatted as (table alias, field name, friendly name) 
#         self.table_fields = [
#             ('u', 'id', 'Primary ID'),
#             ('u', 'first_name', 'First Name'),
#             ('u', 'last_name', 'Last Name'),
#             ('u', 'email', 'Email Address'),
#             ('u', 'phone_number', 'Phone Number'),
#             ('am', 'address1', 'Mailing Address 1'),
#             ('am', 'address2', 'Mailing Address 2'),
#             ('am', 'city', 'City'),
#             ('am', 'state', 'State'),
#             ('am', 'zip_code', 'Zip Code'),
#             ('m', 'household_info', 'Individuals in Household')
#             ]
        
#         # Define the history tables and their corresponding live-table alias
#         # Formatted as (live-table alias, history table name, field name, live-table name)
#         # Note that this only uses the mailing address
#         self.hist_tables = [
#             ('u', 'app_userhist', 'historical_values', 'app_user'),
#             ('am', 'app_addresshist', 'historical_values', 'app_address'),
#             ('h', 'app_householdhist', 'historical_values', 'app_household'),
#             ('m', 'app_householdmembershist', 'historical_values', 'app_householdmembers'),
#             ]
        
#         # Start filtering with non-archived records
#         self.where_framework = """ where u."is_archived"=false """
        
#         # Gather all active programs
#         cursor = self.conn.cursor()
#         cursor.execute(
#             """select id, program_name, friendly_name from public.app_iqprogramrd where is_active=True"""
#             )
#         self.active_programs = cursor.fetchall()
#         cursor.close()


#     def _convert_extract(
#             self,
#             field_list: Union[list, tuple],
#             db_output: Union[list, tuple],
#             ) -> pd.core.frame.DataFrame:
#         """
#         Convert input to pandas dataframe.

#         Parameters
#         ----------
#         field_list : Union[list, tuple]
#             List/tuple of string field names.
#         db_output : Union[list, tuple]
#             List/tuple of tuples, directly from database API output.

#         Raises
#         ------
#         TypeError
#             Raised if an input type is incorrect.

#         Returns
#         -------
#         pd.core.frame.DataFrame
#             Pandas DataFrame represenation of the database output data.

#         """
        
#         if not (isinstance(db_output, (list, tuple)) and isinstance(db_output[0], (list, tuple))):
#             raise TypeError("db_output must be a list/tuple of list/tuples (directly from database output)")
            
#         if not isinstance(field_list, (list, tuple)):
#             raise TypeError("field_list must be a list/tuple")
            
#         df = pd.DataFrame(db_output, columns=field_list)
        
#         # Massage the phone number value (if exists)
#         try:
#             df['Phone Number'] = df[['Phone Number']].applymap(
#                 lambda x: f"NEW VALUE: ({x[-10:-7]}) {x[-7:-4]}-{x[-4:]}" if x is not None and not x.startswith('+') \
#                     else f"({x[2:5]}) {x[5:8]}-{x[8:12]}" if x is not None else None
#                 )
#         except KeyError:
#             pass
        
#         # Convert the 'Individuals in Household' dictionary to pretty format
#         # (if exists)
#         try:
#             df['Individuals in Household'] = df[['Individuals in Household']].applymap(
#                 lambda x: f"{x['modifier']}" + f"{len(x['persons_in_household'])} individual(s); " + ', '.join(
#                     [f"{y['name']} (DOB: {y['birthdate']})" for y in x['persons_in_household']]
#                     ) if x is not None else None
#                 )
#         except KeyError:
#             pass
        
#         return(df)    

#     def _connect(self):
#         # Construct connection string and connect
#         self.conn = psycopg2.connect(
#             "host={hst} user={usr} dbname={dbn} password={psw} sslmode={ssm}".format(
#                 hst=self.host,
#                 usr=self.user,
#                 dbn=self.dbname,
#                 psw=self.cred.password(),
#                 ssm='require')
#             )  
            

# TODO: update to use typer
class Extract:
    
    def __init__(
            self,
            output_file_dir=None,
            user_files_dir=None,
            filename_suffix='IQ Applicants.csv',
            export_type='ALL',
            interactive=False,
            **kwargs,
            ):

        self.output_file_dir = output_file_dir
        self.user_files_dir = user_files_dir

        # Ensure export_type is a valid value
        export_type = export_type.upper()
        if not export_type in ('ALL', 'INCOME', 'PROGRAM', 'INCOMPLETE'):
            raise Exception("export_type must be 'ALL', 'INCOME', 'PROGRAM', or 'INCOMPLETE'")
        
        self._initialize_vars()
        self.select_framework = """
            select {fields} from public.app_user u
            left join (select * from public.app_address ia 
                inner join public.app_addressrd iar on iar.id=ia.mailing_address_id) am on am.user_id=u.id
            left join public.app_household h on h.user_id=u.id
            left join public.app_householdmembers m on m.user_id=u.id
            {additionalJoin}

            {wherePlaceholder}
            
            order by u.id asc
            """   
        # Start filtering with non-archived records
        self.where_framework = """ where u."is_archived"=false """

        # Use different fields for certain program(s)
        self.table_fields = [
                ('u', 'id', 'Primary ID'),
                ('u', 'first_name', 'First Name'),
                ('u', 'last_name', 'Last Name'),
                ('u', 'email', 'Email Address'),
                ('u', 'phone_number', 'Phone Number'),
                ('am', 'address1', 'Mailing Address 1'),
                ('am', 'address2', 'Mailing Address 2'),
                ('am', 'city', 'City'),
                ('am', 'state', 'State'),
                ('am', 'zip_code', 'Zip Code'),
                ('m', 'household_info', 'Individuals in Household')
            ]

        self.hist_tables = [
            ('u', 'UserHist', 'historical_values', 'app_user', 'User'),
            ('am', 'AddressHist', 'historical_values', 'app_address', 'Address'),
            ('h', 'HouseholdHist', 'historical_values', 'app_household', 'Household'),
            ('m', 'HouseholdMembersHist', 'historical_values', 'app_householdmembers', 'HouseholdMembers'),
            ]

        if self.output_file_dir is None:
            self.output_file_dir = Path(self.OUTPUT_FILES_DIR)
        if self.user_files_dir is None:
            self.user_files_dir = Path(self.USER_FILES_SAVE_DIR)

        self.filename_suffix = filename_suffix
        self.interactive = interactive      
        
        # Initialize params
        # self.getfoco = GetFoco(output_file_dir, **kwargs)
        # self.user_files_dir = Path(user_files_dir)
        self.kwargs = kwargs
        
        # if not self.interactive:
        #     try:
                
        #         if export_type == 'INCOME':
        #             # Run income verification extract
        #             self.export_income()
        #         elif export_type == 'PROGRAM':
        #             # Run program extracts
        #             return self.export_programs()
        #         elif export_type == 'INCOMPLETE':
        #             # Run list of incomplete applications
        #             # self.export_incomplete()
        #             warnings.warn("WARNING: export_incomplete() should be run here, but isn't complete yet")
        #         elif export_type == 'ALL':
        #             self.run_all()
            
        #     except:
        #         raise
                
        #     finally:
        #         self.getfoco.conn.close()

    def _convert_extract(
            self,
            field_list: Union[list, tuple],
            db_output: Union[list, tuple],
            ) -> pd.core.frame.DataFrame:
        """
        Convert input to pandas dataframe.

        Parameters
        ----------
        field_list : Union[list, tuple]
            List/tuple of string field names.
        db_output : Union[list, tuple]
            List/tuple of tuples, directly from database API output.

        Raises
        ------
        TypeError
            Raised if an input type is incorrect.

        Returns
        -------
        pd.core.frame.DataFrame
            Pandas DataFrame represenation of the database output data.

        """
        
        if not (isinstance(db_output, (list, tuple)) and isinstance(db_output[0], (list, tuple))):
            raise TypeError("db_output must be a list/tuple of list/tuples (directly from database output)")
            
        if not isinstance(field_list, (list, tuple)):
            raise TypeError("field_list must be a list/tuple")
        
        df = pd.DataFrame(db_output, columns=field_list)
        
        # Massage the phone number value (if exists)
        try:
            df['Phone Number'] = df[['Phone Number']].applymap(
                lambda x: f"NEW VALUE: ({x[-10:-7]}) {x[-7:-4]}-{x[-4:]}" if x is not None and not x.startswith('+') \
                    else f"({x[2:5]}) {x[5:8]}-{x[8:12]}" if x is not None else None
                )
        except KeyError:
            pass
        
        # Convert the 'Individuals in Household' dictionary to pretty format
        # (if exists)
        try:
            df['Individuals in Household'] = df[['Individuals in Household']].applymap(
                lambda x: f"{x['modifier']}" + f"{len(x['persons_in_household'])} individual(s); " + ', '.join(
                    [f"{y['name']} (DOB: {y['birthdate']})" for y in x['persons_in_household']]
                    ) if x is not None else None
                )
        except KeyError:
            pass
        
        return(df)  
            
    def _initialize_vars(self):
        ## Initialize global vars
        try:
            fileDir = Path(__file__).parent
        except NameError:   # dev
            fileDir = Path.cwd()
        
        with open(
                fileDir.parent.parent.joinpath('.env.deploy'),
                'r',
                encoding='utf-8',
                ) as f:
            secrets_dict = loads(f.read())
            
        for key in secrets_dict.keys():
            setattr(self, key, secrets_dict[key])
            
    def _mark_updates(
            self,
            # cursor: psycopg2.extensions.cursor,
            field_list: list,
            record_list: list,
            ) -> (list, list):
        """
        Mark each record in record_list with any updates and output all
        records.
        
        While all input records are included in the output, only the values in 
        each record that are either identifying or have been updated (or both)
        will be included.

        Parameters
        ----------
        cursor : psycopg2.extensions.cursor
            Cursor for the database connection.
        field_list : list
            List of fields associated with each record element.
        record_list : list
            List of records from the database to check for and mark with updates.

        Raises
        ------
        Exception
            Raised if workaround finds an unexpected issue.

        Returns
        -------
        (list, list)
            Returns the list of records and a list of Booleans describing
            which records have been updated (True === the matching index has
            been updated), respectively.

        """
        idFieldIdx = next(iter(inidx for inidx,x in enumerate(field_list) if x[1]=='id'))
        truncFieldsToUse = [x[:2] for x in field_list]
        outputList = []    # initialize output list
        isUpdatedList = []    # initialize the output list of bools
        
        for idxitm,itm in enumerate(record_list):
            # Gather the table(s) that were updated
            tableCheckList = list(set([x[0] for x in field_list]))
            
            tableCheckOut = list(User.objects.select_related(
                'householdmembers',
                'household',
                'address__mailing_address'
            ).filter(
                is_archived=False,
                id=itm[idFieldIdx] # user id in list
            ).values_list(
                'is_updated',
                'householdmembers__is_updated',
                'address__is_updated'
            ))[0]
            # test = self.select_framework.format(
            #         additionalJoin="",
            #         wherePlaceholder=self.where_framework + """ and u."id"={}""".format(itm[idFieldIdx]),
            #         fields=', '.join([f"""{x}."is_updated" """ for x in tableCheckList]),
            #     )
            
            # cursor.execute(test)
            # tableCheckOut = cursor.fetchone()
            
            # Initialize list of updated fields and define the identifying
            # fields to include in the extract regardless of update
            updatedFields = []
            identifyingFields = [
                ('u', 'id'),
                ('u', 'first_name'),
                ('u', 'last_name'),
                ('u', 'email'),
                ]
            for updidx,isupdated in enumerate(tableCheckOut):
                if isupdated:
                    # If updated, get the fields that changed and add the 
                    # new values to the output
                    tableRef = next(iter(x for x in self.hist_tables if x[0]==tableCheckList[updidx]))
                    modelName = tableRef[1]
                    modelClass = getattr(models, modelName)

                    histOut = modelClass.objects.filter(
                        user_id=itm[idFieldIdx]
                    ).values(
                        tableRef[2]
                    ).order_by(
                        '-id'
                    ).first()['historical_values']
                    
                    # TODO: ask Tim about the catch block here...what is it doing and does it need to be mimicked
                    # cursor.execute(
                    #     # Use only the *latest* historical record
                    #     """select "{fdv}" from public.{tbl} where user_id={usr} order by "created" desc limit 1""".format(
                    #         fdv=tableRef[2],
                    #         tbl=tableRef[1],
                    #         usr=itm[idFieldIdx],
                    #         )
                    #     )
                    # try:
                    #     histOut = cursor.fetchone()[0]
                    # except TypeError:
                    #     histOut = {"mailing_address_id": 0, "eligibility_address_id": 0}
                    
                    if modelName=='AddressHist' and histOut is None:
                        histOut = {"mailing_address_id": 0, "eligibility_address_id": 0}
                    
                    # raise Exception('breakpoint')
                    
                    # Define updatedFields as (index of record_list, 
                    # historical value) (if the historical value is an 
                    # identifying field)
                    
                    # Address is the only field that stores IDs - strip
                    # '_id' and use the mailing address (only) parts
                    if tableCheckList[updidx] == 'am':
                        if 'mailing_address_id' in histOut.keys():
                            updatedFields.extend(
                                [
                                    (truncFieldsToUse.index((tableRef[0], 'address1')), None),
                                    (truncFieldsToUse.index((tableRef[0], 'address2')), None),
                                    (truncFieldsToUse.index((tableRef[0], 'city')), None),
                                    (truncFieldsToUse.index((tableRef[0], 'state')), None),
                                    (truncFieldsToUse.index((tableRef[0], 'zip_code')), None),
                                    ]
                                )
                    else:
                        # Loop through each key to determine what to do with it
                        for key in histOut.keys():
                            # If any identification fields were updated, gather
                            # the old values as well
                            if (tableRef[0], key) in identifyingFields:
                                histVal = histOut[key]
                            else:
                                histVal =  None
                                
                            # Check for whether the field in question is in the
                            # list of fields to output (truncFieldsToUse)
                            try:
                                outVal = (
                                    truncFieldsToUse.index(
                                        (tableRef[0], key)),
                                    histVal,
                                    )
                                
                            except ValueError:  # index not found
                                pass
                            else:
                                updatedFields.append(outVal)
                     
            # Define indices that weren't updated to keep in the extract
            nonUpdatedIdxToKeep = [truncFieldsToUse.index(x[:2]) for x in identifyingFields]
            # Mark updated values as well as 'old value' for identifying
            # fields
            updatedVals = []
            updatedIdx = [x[0] for x in updatedFields]
            for iteridx,iteritm in enumerate(itm):
                try:
                    updatedFieldVal = next(iter(x for x in updatedFields if x[0]==iteridx))
                except StopIteration:   # index is not in updatedFields
                    if iteridx in nonUpdatedIdxToKeep:
                        updatedVals.append(iteritm)
                    else:
                        updatedVals.append(None)
                else:
                    # If this is the JSON value, insert 'NEW VALUE' as a key
                    if isinstance(iteritm, dict):
                        ############
                        # Workaround to account for is_updated being set
                        # each time /household_members is visited (see
                        # https://github.com/Get-Your/Get-Your-utils/issues/4
                        # for details). If this isn't an actually-updated
                        # field, this copies the functionality of the
                        # StopIteration case
                        
                        # Verify this is the jsonIdx value (the household_info
                        # field from GetFoco.table_fields)
                        jsonIdx = next(iter(idx for idx,x in enumerate(self.table_fields) if x[1]=='household_info'))
                        if iteridx != jsonIdx:  # shouldn't exist
                            raise Exception("is_updated workaround: JSON value found that isn't from app_householdmembers")
                            
                        # Re-gather the historical values
                        histOut = HouseholdMembersHist.objects.filter(
                            user_id=itm[idFieldIdx]
                        ).values(
                            'historical_values'
                        ).order_by(
                            'created'
                        )[0]
                    
                        # cursor.execute(
                        #     # Use only the *latest* historical record
                        #     """select "historical_values" from "public"."app_householdmembershist" where "user_id"={usr} order by "created" desc limit 1""".format(
                        #         usr=itm[idFieldIdx],
                        #         )
                        #     )
                        # histOut = cursor.fetchone()[0]
                        
                        # Build new dicts with just name and birthdate
                        # (since that's what we care about for the updates)
                        
                        iterCheck = [
                            {
                                key: listitm[key] for key in ['name', 'birthdate']
                                }
                            for listitm in iteritm['persons_in_household']
                            ]
                        
                        histCheck = [
                            {
                                key: listitm[key] for key in ['name', 'birthdate']
                                }
                            for listitm in histOut['historical_values']['household_info']['persons_in_household']
                            ]
                        if iterCheck == histCheck:
                            if iteridx in nonUpdatedIdxToKeep:
                                updatedVals.append(iteritm)
                            else:
                                updatedVals.append(None)
                        else:
                        ############
                        
                            iteritm.update({'modifier': 'NEW VALUE: '})
                            updatedVals.append(iteritm)
                    else:
                        updatedVals.append(f"OLD VALUE: {updatedFieldVal[1]}, NEW VALUE: {iteritm}" if updatedFieldVal[1] is not None else f"NEW VALUE: {iteritm}")
                    
            # Append the updated values to the output list. If no business
            # values were truly updated, this will only include identifying
            # vals
            outputList.append(tuple(updatedVals))
            # If any of the affected fields are actual updates, write them to
            # the isUpdatedList for reference
            if all(x is None for idx,x in enumerate(updatedVals) if idx not in nonUpdatedIdxToKeep):
                isUpdatedList.append(False)
            else:
                isUpdatedList.append(True)
                
            assert len(outputList) == len(isUpdatedList)
            
        return (outputList, isUpdatedList)
    
    def run_all(self):
        """ Run *all* extracts (standard, all applicants, and app feedback).
        
        Note that this is an automated function.
        
        """
        
        # Export all applicants
        self.export_global()
        
        # Run standard extracts
        self.export_income()
        self.export_programs()

        # Export user feedback
        self.export_feedback()

    def export_global(
            self,
            save_file: bool = True,
            save_dir: Union[str, Path] = None,
            ) -> None:
        """
        Export the global standard extract (for IQ program lead(s)).

        Parameters
        ----------
        save_file : bool, optional
            Save the file (rather than just run the calculations in memory).
            The default is True.
        save_dir : Union[str, Path], optional
            Directory to save the file. The default is
            self.getfoco.output_file_dir.

        Returns
        -------
        None

        """
        
        if self.getfoco.conn.closed == 1:
            self.getfoco._connect()
        
        cursor = self.getfoco.conn.cursor()

        # Use table_fields along with all 'is_enrolled' fields in
        # app_iqprograms
        tableFieldsStr = ','.join(
            [f'{x[0]}."{x[1]}"' for x in self.getfoco.table_fields]
            )
        
        # Additional field cases that need no preprocessing for the query
        # The BOOL_AND() output will result in
            # True if the user is enrolled in the program
            # False if the user is not enrolled
            # NULL if the user has not applied
        # The second element is to match the formatting of table_fields
        additionalFieldCases = [
            (
                f"""BOOL_AND(CASE WHEN iq."program_id"={pid} AND iq."is_enrolled"=true THEN true WHEN iq."program_id"={pid} AND iq."is_enrolled"=false THEN false WHEN iq."program_id"={pid} AND iq."is_enrolled" is null THEN null end)""",
                '',
                f'Enrolled in {pfd}',
                ) for pid,pnm,pfd in self.getfoco.active_programs
            ]
        
        # Gather the list of fields: table_fields + active_programs
        friendlyFields = [x[2] for x in self.getfoco.table_fields+additionalFieldCases]

        queryStr = self.getfoco.select_framework.format(
            additionalJoin='left join public.app_iqprogram iq on iq.user_id=u.id',
            fields="{},{}".format(
                tableFieldsStr,
                ','.join(
                    [f'{x[0]}' for x in additionalFieldCases]
                    ),
                ),
            # Since we're aggregating the CASE conditions, need to group by
            # all other fields. Hijack wherePlaceholder for this:
            wherePlaceholder=self.getfoco.where_framework + f"group by {tableFieldsStr}",
            )    
            
        cursor.execute(queryStr)
        dbOut = cursor.fetchall()
        
        # Convert to pandas DataFrame
        df = self.getfoco._convert_extract(friendlyFields, dbOut)
            
        if save_file:
            # Define save_path if not explicitly stated
            if save_dir is None:
                save_dir = self.getfoco.output_file_dir
            else:
                save_dir = Path(save_dir)
                
            save_path = save_dir.joinpath(
                '{dt} All {suf}'.format(
                    dt=pendulum.now().date(),
                    suf=self.filename_suffix,
                    ),
                )

            # Start a file with the legend for program enrollment
            with open(save_path, 'w+') as f:
                f.write(
                    "Program legend:, TRUE = 'user is enrolled', FALSE = 'user is not enrolled', No Value = 'user has not applied'\n"
                    )
                f.write("\n")
            
            # Append dataframe to file
            df.to_csv(
                save_path,
                index=False,
                mode='a',
                )
    
            print("Extract saved!")

        cursor.close()
    
    def export_income(self):
        """
        Export the program-specific standard extracts (for individual program
        lead(s)).
        
        Parameters
        ----------
        self
    
        Returns
        -------
        None.
    
        """
        
        # Parse kwargs; start with initialized defaults
        save_file = True if not 'save_file' in self.kwargs.keys() else self.kwargs['save_file']
        ids_to_warn = [] if not 'ids_to_warn' in self.kwargs.keys() else self.kwargs['ids_to_warn']

        if self.getfoco.conn.closed == 1:
            self.getfoco._connect()
            
        cursor = self.getfoco.conn.cursor()

        # Gather all users who need their income verified
        # is_verified=false filters out already-verified applicants; the user
        # has completed the application when a record here exists
        
        # The additionalJoin has two different segments of eligibilityprogram
        # joins:
            # - the first links the user's eligibility address to ensure
            # it's verified
            # - the next ensures there are users that have an active program
            # - the last ensures that all records in eligibilityprogram have
            # files that have been uploaded
        queryStr = self.getfoco.select_framework.format(
            additionalJoin="""
            left join (select * from public.app_address ia 
                inner join public.app_addressrd iar on iar.id=ia.eligibility_address_id) ae on ae.user_id=u.id
            inner join (select distinct ie.user_id from public.app_eligibilityprogram ie
                left join public.app_eligibilityprogramrd ier on ie.program_id=ier.id where ier.is_active=true) e on e.user_id=u.id""",
            fields=', '.join([f'{x[0]}."{x[1]}"' for x in self.getfoco.table_fields]),
            wherePlaceholder=self.getfoco.where_framework + """ and h."is_income_verified"=false 
            and am.is_verified=true 
            and ae.is_verified=true 
            and u."id" not in (select distinct ie.user_id from public.app_eligibilityprogram ie
                left join public.app_eligibilityprogramrd ier on ie.program_id=ier.id where ier.is_active=true and ie.document_path='')""",
            )
        cursor.execute(queryStr)
        dbInitOut = cursor.fetchall()
        
        if len(dbInitOut)>0:
            
            # Gather the index of the JSON data
            jsonIdx = next(iter(idx for idx,x in enumerate(self.getfoco.table_fields) if x[1]=='household_info'))
            
            ############
            # Workaround to account for change in identification file upload
            # (see https://github.com/Get-Your/Get-Your-utils/issues/12 for
            # details). This will write dbOut based on whether
            # identification_path exists in the JSON keys
            dbOut = []
            for idx,itm in enumerate(dbInitOut):
                if all('identification_path' in x.keys() for x in itm[jsonIdx]['persons_in_household']):
                    dbOut.append(itm)
            # Once removed, rename dbInitOut to dbOut
            ############
            
            # Add empty 'modifier' key to 'household_info' JSON values (empty
            # indicates 'not a modified value')
            for idx,itm in enumerate(dbOut):
                itm[jsonIdx].update({'modifier': ''})
                dbOut[idx] = tuple(list(itm[:jsonIdx])+[itm[jsonIdx]]+list(itm[jsonIdx+1:]))
                
            warnings.warn('WARNING: literal_eval() is potentially dangerous. Best to find a different solution to storing multiple files.')
            outFieldList = self.getfoco.table_fields+[('','','Uploaded File(s)'),]
            # Gather list of uploaded file(s)
            queryStr = """select u."id", e."friendly_name", e."document_path" from public.app_user u
                        right join (select * from public.app_eligibilityprogram ie
                            left join public.app_eligibilityprogramrd ier on ie.program_id=ier.id where ier.is_active=true) e on e.user_id=u.id
                        order by u.id asc"""
            cursor.execute(queryStr)
            filesOut = cursor.fetchall()
            
            # Parse files by user and create friendly filename readout
            userIdIdx = next(iter(idx for idx,x in enumerate(self.getfoco.table_fields) if x[0]=='u' and x[1]=='id'))
            for idx,itm in enumerate(dbOut):
                userId = itm[userIdIdx]
                
                # Gather files and parse into string
                fileList = sorted([x for x in filesOut if x[0]==userId])
                # Use only program names
                fileStr = ', '.join(
                    [x[1] for x in fileList]
                    )
                # # Use program names and document paths
                # fileStr = '; '.join(
                #     ["{}: {}".format(x[1], ', '.join([y.split('/')[1] for y in ast.literal_eval(x[2])])) for x in fileList]
                #     )
                
                dbOut[idx] = tuple(
                    list(dbOut[idx]) + [fileStr]
                    )
                
            # Convert to dataframe, using the friendly field names in outFieldList
            df = self.getfoco._convert_extract(
                [x[2] for x in outFieldList],
                dbOut,
                )

            # Add column for 'Income Verified' and set all to False
            df = df.assign(
                **{'Income Verified': [False]*len(df)},
                )
            
            # Set a warning when specific IDs are included in the extract
            warningList = []
            for iditm in ids_to_warn:
                try:
                    _ = list(df['Primary ID'].values).index(iditm)
                except ValueError:
                    pass
                else:
                    warningList.append(iditm)
                   
            if len(warningList) > 0:
                userContinue = Confirm.ask(
                    "\nWARNING: ID{} ({}) from [green]ids_to_warn[/green] found in this extract. Continue?".format(
                        's' if len(warningList)>1 else '',
                        ', '.join([str(x) for x in warningList]),
                        )
                    )
                if not userContinue:
                    raise KeyboardInterrupt("User cancelled file creation based on ID-specific warning")
                    
            if save_file:
                # Write to file
                df.to_csv(
                    self.getfoco.output_file_dir.joinpath(
                        '{dt} {prg} {suf}'.format(
                            dt=pendulum.now().date(),
                            prg='Income Verification',
                            suf=self.filename_suffix,
                            ),
                        ),
                    index=False,
                    )
        
                print("Extract saved!")       
                    
            print(f"Saving 'all' and 'feedback' exports to {self.user_files_dir.stem} folder")
            
            self.export_global(
                save_dir=self.user_files_dir,
                )
            
            self.export_feedback(
                save_dir=self.user_files_dir,
                )
                    
        cursor.close()

        return(df)
        
    def export_programs(self):
        """
        Export the program-specific standard extracts (for individual program
        lead(s)).
        
        Parameters
        ----------
        self
    
        Returns
        -------
        None.
    
        """
        
        # Parse kwargs; start with initialized defaults
        save_file = True if not 'save_file' in self.kwargs.keys() else self.kwargs['save_file']
        reset_updates = True if not 'reset_updates' in self.kwargs.keys() else self.kwargs['reset_updates']
        ids_to_warn = [] if not 'ids_to_warn' in self.kwargs.keys() else self.kwargs['ids_to_warn']
        mark_enrolled = True if not 'mark_enrolled' in self.kwargs.keys() else self.kwargs['mark_enrolled']
        
        if reset_updates != mark_enrolled:
            raise TypeError("reset_updates and mark_enrolled must be set to the same value")
        
        # if self.getfoco.conn.closed == 1:
        #     self.getfoco._connect()
        
        # cursor = self.getfoco.conn.cursor()

        # Keep list of *all* users involved in extracts - these users will have
        # is_updated reset for all applicable tables after extracts are saved
        # (because any updates will have been part of the applicable extracts)
        activePrograms = IQProgramRD.objects.filter(is_active=True).values_list('id', 'program_name', 'friendly_name')
        allAffectedUsers = []
        for programId,programname,friendlyname in activePrograms:
            # Initialize dbOut (there will be multiple queries) and their
            # respective 'notes' (to be combined in the extract)
            dbOut = []
            notesList = []
            # Keep running list of users for this program that were processed
            # in previous steps (to ignore in subsequent steps)
            alreadyProcessedUsers = []
            
            if programname in ('spin', 'gardens'):
                fieldsToUse = [x for x in self.table_fields if x[1] in (
                    'id',
                    'first_name',
                    'last_name',
                    'email'
                    )]
            else:
                fieldsToUse = self.table_fields
            
            # Define the output fields for the extract
            outFieldList = [('','','Notes'),] + fieldsToUse
            
            # Find the index of the 'id' field for later reference
            idFieldIdx = next(iter(inidx for inidx,x in enumerate(fieldsToUse) if x[1]=='id'))
            
            ## Gather new applicants for the current program
            
            # For additionalJoin:
                # - brings in the IQ programs' information        
            # Note that mailing and eligibility address verifications are
            # checked before income verification, so they don't need to be
            # duplicated here
            
            # In the where clause:
                # - i.is_enrolled=false filters out already-enrolled users (the
                # user has applied when a record exists
            #     self.select_framework = """
            
            # Define the standard query framework
            # This uses the mailing address for all extracts
            # select {fields} from public.app_user u
            # left join (select * from public.app_address ia 
            #     inner join public.app_addressrd iar on iar.id=ia.mailing_address_id) am on am.user_id=u.id
            # left join public.app_household h on h.user_id=u.id
            # left join public.app_householdmembers m on m.user_id=u.id
            # {additionalJoin}

            # {wherePlaceholder}
            
            # order by u.id asc
            # """   
            # Start filtering with non-archived records
            # self.where_framework = """ where u."is_archived"=false """

            usersStuckInRenewal = User.objects.select_related(
                'household',
                'iq_programs__program',
            ).values_list(
                'iq_programs__user_id',
                'iq_programs__program_id',
            ).annotate(
                program_count=Count('iq_programs__program_id')
            ).filter(
                is_archived=False,
                household__is_income_verified=True,
                iq_programs__program__program_name=programname,
                iq_programs__is_enrolled=False,
                program_count__gt=1
            )

            usersStuckInRenewalIds = [item[0] for item in usersStuckInRenewal]

            newOut = list(User.objects.select_related(
                'householdmembers',
                'household',
                'iq_programs__program',
                'address__mailing_address'
            ).filter(
                is_archived=False,
                household__is_income_verified=True,
                iq_programs__program__program_name=programname,
                iq_programs__is_enrolled=False,
            ).values_list(
                'id',
                'first_name',
                'last_name',
                'email',
                'phone_number',
                'address__mailing_address__address1',
                'address__mailing_address__address2',
                'address__mailing_address__city',
                'address__mailing_address__state',
                'address__mailing_address__zip_code',
                'householdmembers__household_info',
            ).exclude(
                # id__in=alreadyProcessedUsers, alreadyProcessedUsers is empty here
                id__in=usersStuckInRenewalIds,
            ).order_by('id'))

            # newApplicantQuery = self.select_framework.format(
            #     additionalJoin="""
            #     right join (select * from public.app_iqprogram ii
            #         left join public.app_iqprogramrd iir on iir.id=ii.program_id) i on i.user_id=u.id
            #     """,
            #     wherePlaceholder=self.where_framework + """ and h."is_income_verified"=true and i."is_enrolled"=false and i."program_name"='{prg}' {prc}""".format(
            #         prg=programname,
            #         prc="""and u."id" not in ({})""".format(', '.join([str(x) for x in alreadyProcessedUsers])) if len(alreadyProcessedUsers)>0 else "",
            #         ),
            #     fields=','.join([f'{x[0]}."{x[1]}"' for x in fieldsToUse]),
            #     )
            
            # cursor.execute(newApplicantQuery)
            # newOut = cursor.fetchall()
            
            # Add empty 'modifier' key to 'household_info' JSON values, if
            # applicable (empty indicates 'not a modified value')
            try:
                jsonIdx = next(iter(idx for idx,x in enumerate(fieldsToUse) if x[1]=='household_info'))
            except StopIteration:
                pass
            else:
                for idx,itm in enumerate(newOut):
                    if itm[jsonIdx] is not None:
                        itm[jsonIdx].update({'modifier': ''})
                    newOut[idx] = tuple(list(itm[:jsonIdx])+[itm[jsonIdx]]+list(itm[jsonIdx+1:]))
            
            dbOut.extend(newOut)
            notesList.extend([None]*len(newOut))
            alreadyProcessedUsers.extend([x[idFieldIdx] for x in newOut])
            ## Gather currently-enrolled applicants of the current program who
            ## have updated their information
            
            # For additionalJoin:
                # - brings in the IQ programs' information        
        
            # In the where clause:
                # - i.is_enrolled=true already covers h.is_income_verified, so
                # there's no need for this
            
            updateOut = User.objects.select_related(
                'householdmembers',
                'household',
                'iq_programs__program',
                'address__mailing_address'
            ).filter(
                is_archived=False,
                iq_programs__program__program_name=programname,
                iq_programs__is_enrolled=True,
                is_updated=True
            ).exclude(
                id__in=alreadyProcessedUsers
            ).values_list(
                'id',
                'first_name',
                'last_name',
                'email',
                'phone_number',
                'address__mailing_address__address1',
                'address__mailing_address__address2',
                'address__mailing_address__city',
                'address__mailing_address__state',
                'address__mailing_address__zip_code',
                'householdmembers__household_info'
            ).order_by('id')
            # updatedInfoQuery = self.select_framework.format(
            #     additionalJoin="""
            #     right join (select * from public.app_iqprogram ii
            #         left join public.app_iqprogramrd iir on iir.id=ii.program_id) i on i.user_id=u.id
            #     """,
            #     wherePlaceholder=self.where_framework + """ and i."is_enrolled"=true and i."program_name"='{prg}' and ({upd}) {prc}""".format(
            #         prg=programname,
            #         upd='or '.join([f"""{x}."is_updated" """ for x in set([x[0] for x in fieldsToUse])]),
            #         prc=f"""and u."id" not in ({', '.join([str(x) for x in alreadyProcessedUsers])})""" if len(alreadyProcessedUsers)>0 else '',
            #         ),
            #     fields=','.join([f'{x[0]}."{x[1]}"' for x in fieldsToUse]),
            #     )
            
            # cursor.execute(updatedInfoQuery)
            # updateOut = cursor.fetchall()
            
            # For each user in updateOut, find the information that changed
            # and prepend 'UPDATE ONLY: ' in the extract
            recordsOut, updatedBools = self._mark_updates(
                # cursor,
                fieldsToUse,
                updateOut,
                )

            # Use updatedBools to remove records with erroneous is_updated val
            updateList = [x for x,y in zip(recordsOut, updatedBools) if y]
            
            dbOut.extend(updateList)
            notesList.extend(['UPDATE ONLY']*len(updateList))
            alreadyProcessedUsers.extend([x[idFieldIdx] for x in updateList])
           
            if len(dbOut)>0:
                # Convert to dataframe, using the friendly field names in outFieldList
                # Append each element of notesList to the end of each dbOut element
                df = self._convert_extract(
                    [x[2] for x in outFieldList],
                    [tuple([x] + list(y)) for x,y in zip(notesList, dbOut)],
                    )

                # Add column for 'Enrolled in Program' (if `not mark_enrolled`)
                # and set based on notes field
                if not mark_enrolled:
                    # NOTE that this assumes a user is already enrolled only if
                    # notes starts with 'update' (case-insensitive)
                    df = df.assign(
                        **{'Enrolled in Program': [True if isinstance(x, str) and x.lower().startswith('update') else False for x in df['Notes']]},
                        )
                
                ## Data validation
                
                # User IDs in question
                userIds = df['Primary ID'].tolist()
                
                # cleanUserIds = self.removeIdsWithRenewalIssues(userIds)
                
                # Ensure none of the users have more than one record per
                # program. This would likely signify a renewal process that got
                # stuck short of completing
                
                # renewalCheckQuery = "select user_id, program_id, count(*) from public.app_iqprogram where user_id in ({}) group by user_id, program_id".format(
                #     ','.join(['%s']*len(userIds)),
                # )
            
                # cursor.execute(
                #     renewalCheckQuery,
                #     userIds,
                # )
                # renewalCheckOut = cursor.fetchall()

                # assert all(x[2]==1 for x in renewalCheckOut)
                
                # Check for prior enrollments for new users
                
                # This has been an issue with GTR (and probably others, but
                # since they're not payments they haven't been an issue) with
                # the v1 app, so we need to verify it doesn't continue
                # happening

                # Use case-insensitive programname when searching to catch all
                # files with older naming conventions as well
                fileList = [x for x in os.listdir(self.output_file_dir) if fnmatch(x, f"*{programname}*")]
                
                # With renewal availability in Get-Your v4, 'already enrolled'
                # here is essentially meaningless. Use only the current-year
                # files as a doublecheck that a user hasn't been enrolled more
                # than once
                fileList = [x for x in fileList if int(re.match(r'(\d{4}).*', x).group(1))==pendulum.today().year]

                # Initialize the list of those possibly already enrolled
                possibleAlreadyEnrolled = []
                
                # Search through all files in fileList to ensure there isn't
                # a matching 'Primary ID' + 'Last Name' that had been previously
                # enrolled
                
                # Note that this only checks when Notes is None (to avoid
                # checking for either 'update' or 'renewal')
                newDf = df[df['Notes'].apply(lambda x: x is None)]
                newData = list(
                    zip(
                        newDf['Primary ID'].values,
                        newDf['Last Name'].values,
                        )
                    )
                for filename in fileList:
                    try:
                        checkDf = pd.read_csv(
                            self.output_file_dir.joinpath(filename),
                            encoding='latin',
                            )
                    except pd.errors.ParserError:
                        # Some issue with reading the file; go to the next
                        continue
                    
                    # Check when Notes is not 'UPDATE ONLY' (only when None or
                    # 'renewal')
                    checkDf = checkDf[checkDf['Notes'].apply(lambda x: x != 'UPDATE ONLY')]
                    
                    # Filter for only enrolled==true if this column exists;
                    # else, assume all users in the extract are enrolled
                    try:
                        checkDf = checkDf[checkDf['Enrolled in Program'].apply(lambda x: x==True)]
                    except KeyError:
                        pass
                    
                    if len(checkDf) > 0:
                        checkData = list(
                            zip(
                                checkDf['Primary ID'].values,
                                checkDf['Last Name'].values,
                                [filename]*len(checkDf)
                                )
                            )
                        
                        # Check True-filtered checkData against each newData
                        possibleAlreadyEnrolled.extend([x for x in checkData if x[:2] in newData])
                        
                if len(possibleAlreadyEnrolled) > 0:
                    
                    uniqueIds = list(set([x[0] for x in possibleAlreadyEnrolled]))
                    # Use most-recent filename first; reverse the list
                    possibleAlreadyEnrolled.reverse()
                    possibleAlreadyEnrolled = [next(iter(x for x in possibleAlreadyEnrolled if x[0]==idv)) for idv in uniqueIds]
                    
                    console = Console()
                    viewTable = Table("Primary ID", "Last Name", "Found Filename")
                    for iditm,nameitm,fnameitm in possibleAlreadyEnrolled:
                        viewTable.add_row(str(iditm), nameitm, fnameitm)
                    
                    print(f"[bold red]Warning: these users are possibly already enrolled in '{friendlyname}':")
                    console.print(viewTable)

                





                # Set a warning when specific IDs are included in the extract
                warningList = []
                for iditm in ids_to_warn:
                    try:
                        _ = list(df['Primary ID'].values).index(iditm)
                    except ValueError:
                        pass
                    else:
                        warningList.append(iditm)
                       
                if len(warningList) > 0:
                    userContinue = Confirm.ask(
                        "\nWARNING: ID{} ({}) from [green]ids_to_warn[/green] found in the '{}' extract. Continue?".format(
                            's' if len(warningList)>1 else '',
                            ', '.join([str(x) for x in warningList]),
                            programname,
                            )
                        )
                    if not userContinue:
                        raise KeyboardInterrupt("User cancelled file creation based on ID-specific warning")

                # Determine output
                outMsg = []
                if save_file:
                    # Write to file
                    df.to_csv(
                        self.output_file_dir.joinpath(
                            '{dt} {prg} {suf}'.format(
                                dt=pendulum.now().date(),
                                prg=friendlyname,
                                suf=self.filename_suffix,
                                ),
                            ),
                        index=False,
                        )
                    
                    # Once the extract is saved, add the users to the list of
                    # is_updated being reset
                    allAffectedUsers.extend(df['Primary ID'].tolist())
            
                    outMsg.append("extract saved")
                    
                if mark_enrolled:
                    for id in userIds:
                        # UPDATE public.app_iqprogram
                        # SET is_enrolled = true, enrolled_at = now()
                        # WHERE program_id = programid 
                        # and is_enrolled = false
                        # and user_id = any(p_id);
                        iqprogramRecord = IQProgram.objects.filter(
                            user_id=id,
                            program_id=programId
                        )
                        # TODO: uncomment the lines below to save the record
                        # iqprogramRecord.is_enrolled = True
                        # iqprogramRecord.enrolled_at = pendulum.now()
                        # iqprogramRecord.save()
                    # # Mark all users enrolled in the current program by
                    # # executing the setenrolled function
                    # try:
                    #     # Only 100 elements can be input to a function, so
                    #     # limit this to 99 users at a time (plus programname
                    #     # == 100)
                    #     iterLimit = 99
                    #     functionIdx = 0
                    #     numberEnrolled = 0
                    #     while 1:
                    #         functionUsers = userIds[iterLimit*functionIdx:iterLimit*(functionIdx+1)]
                    #         # concatenatedTest = [programname]+functionUsers
                    #         # placeholders = ','.join(['%s']*len(functionUsers))
                    #         # functionQuery = "SELECT public.app_iqprogram_setenrolled(%s,{})".format(
                    #         #     ','.join(['%s']*len(functionUsers)),
                    #         # )
                    #         # cursor.execute(
                    #         #     functionQuery,
                    #         #     [programname]+functionUsers,
                    #         # )
                    #         # functionMsg = cursor.fetchone()[0]

                    #         # iqprogramRecord = IQProgram.objects.get(user_id)
                    #         functionMsg = IQProgram.objects.raw(
                    #             "SELECT app_iqprogram_setenrolled(" + ','.join(['%s']*len(functionUsers)) + ")", [programname, functionUsers]
                    #         )
                        
                    #         # Raise exception if the number enrolled from the
                    #         # function is different than the number of new
                    #         # applicants found above
                    #         numberEnrolled += int(
                    #             re.match(
                    #                 r'Once transaction is committed: (\d*) users? enrolled.*',
                    #                 functionMsg
                    #             ).group(1)
                    #         )

                    #         # Break the loop if all userIds have been input,
                    #         # else iterate functionIdx
                    #         if iterLimit*(functionIdx+1)>=len(userIds):
                    #             break
                    #         functionIdx += 1
                            
                    #     # Take the total enrolled and compare it to the extract
                    #     if int(numberEnrolled) != len(newOut):
                    #         raise AssertionError('Number enrolled is different than new applicants')
                            
                    # except:
                    #     # self.getfoco.conn.rollback()
                    #     raise
                    # else:
                    #     # self.getfoco.conn.commit()
                    #     outMsg.append("users enrolled")
                        
                else:
                    outMsg.append("users were not enrolled")
                    
                # Print any output to the user
                if len(outMsg) > 0:
                    print("{}!".format(' and '.join(outMsg)).capitalize())
                    
                
        # Only reset is_updated values if save_file==True (to ensure the
        # extracts were exported)
        if reset_updates and save_file and len(allAffectedUsers) > 0:
            # Remove duplicates from allAffectedUsers
            allAffectedUsers = list(set(allAffectedUsers))
            print("Don't delete the new exports! Exports created from this script in the future won't include the same 'updated' user(s)")
            
            # Reset all is_updated values in all applicable tables from self.hist_tables[4]
            # TODO: uncomment this when done with testing
            # for tableitm in self.hist_tables:
            #     modelName = tableitm[4]
            #     modelClass = getattr(models, modelName)

            #     allModelsOfClass = modelClass.objects.all()
                
            #     if modelName == 'User':
            #         filteredClassModels = allModelsOfClass.filter(
            #             id__in=allAffectedUsers
            #         )
            #     else:
            #         filteredClassModels = allModelsOfClass.filter(
            #             user_id__in=allAffectedUsers
            #         )

            #     filteredClassModels.update(
            #         is_updated=False
            #     )
            # Reset all is_updated values in all applicable tables
            # for tableitm in self.hist_tables:
            #     # tableitm[3] is the live table name
            #     if tableitm[3] == 'app_user':
            #         fieldName = 'id'
            #     else:
            #         fieldName = 'user_id'
            #     cursor.execute(
            #         """update public.{tbl} set is_updated=false where "{fdn}" in ({vls})""".format(
            #             tbl=tableitm[3],
            #             fdn=fieldName,
            #             vls=', '.join(['%s']*len(allAffectedUsers)),
            #             ),
            #         allAffectedUsers,
            #         )
            
            # self.getfoco.conn.commit()
        else:
            print("Update designations in the database were not reset")

        return [x for x in os.listdir(self.output_file_dir) if x.startswith(str(pendulum.today().year))]

    def export_incomplete(self):
        """
        Export the incomplete applications (e.g. anything that didn't make it
        into the income-verification extract), including the step that the
        applicant got stuck on.

        Parameters
        ----------
        self
    
        Returns
        -------
        None.
    
        """
        
        raise NotImplementedError("This needs to be updated for v2 code - probably using the application completion bitmap (and also the renewal completion bitmap? might be nice to be able to track users who haven't complete renewal)")
        
        if self.getfoco.conn.closed == 1:
            self.getfoco._connect()
        
        cursor = self.getfoco.conn.cursor()
            
        # Use only contact fields in the 'incomplete' extract
        fieldsToExport = [x for x in self.getfoco.table_fields if x[1] in (
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            )]
        idFieldIdx = next(iter(inidx for inidx,x in enumerate(fieldsToExport) if x[1]=='id'))

        # Use these fields to check what step the applicant ended on (the
        # third tuple element is the step number).
        # This will use dashboard.backend.what_page()
        fieldsToVerify = [
            ('aa', 'is_verified', 2),      # If False or NULL (e.g. not True), incomplete step is 2: where do you live?
            ('ae', 'user_id_id', 3),       # If DNE, incomplete step is 3: how long have you lived at this address, how many individuals, enter gross annual household income
            ('am', 'user_id_id', 4),    # If DNE, incomplete step is 4: names and birthdates of individuals
            ('auf', 'user_id', 5),           # If DNE, incomplete step is 5: file selection/upload (NOTE: does not check for specific file uploaded (i.e. that the uploaded files match what was selected), just that files were selected and uploaded)
            ]
        fieldList = ','.join(
                [f'{x[0]}."{x[1]}"' for x in fieldsToExport+fieldsToVerify]
                )
        
        # Add an additional table to the joins
        whereClause = """ left join (select user_id, min(form_id) as form_id from application_user_files group by user_id) auf on auf.user_id=au.id left join dashboard_form df on auf.form_id=df.id"""
        
        whereClause+=""" where au."is_archived"=false and (aa."isInGMA"=true or aa."isInGMA" is NULL)"""
            
        # Append to where clause so that only non-income-verified
        # applicants are exported here
        # Income-verified but without program applications will come later
        whereClause+=""" and (ae."GenericQualified"='PENDING' or ae."GenericQualified" is NULL)"""
        
        # Filter out all IDs that are applicable to the
        # income-verification extract
        idFilterTable = self.export_income(save_file=False)
        whereClause+=""" and au."id" not in ({})""".format(
            ','.join([str(x) for x in idFilterTable.primary_id.records])
            )
            
        queryStr = self.getfoco.select_framework.format(
            fields=fieldList,
            wherePlaceholder=whereClause,   # if not blank, must start with 'where...'
            )    
            
        cursor.execute(queryStr)
        dbOut = cursor.fetchall()
        
        # Go through fieldsToCheck to ensure this hasn't been modified
        # in the last 5 days (so we don't reach out too soon)
        # Note that fieldsToCheck indices/fields match the step number
        fieldsToCheck = [
            ('au', 'modified', ''), # placeholder
            ('au', 'modified', ''),
            ('aa', 'modified', ''),
            ('ae', 'modified', ''),
            ('am', 'modified', ''),
            ('df', 'modified', ''),
            ]
        
        # If there are no incomplete applications, do not continue
        if len(dbOut)>0:
            
            # Create a lookup table to translate the steps
            stepDescription = [
                (2, 'Step 2: Enter address'),
                (3, 'Step 3: How long have you lived at this address, how many individuals in the household, enter gross annual household income'),
                (4, 'Step 4: Names and birthdates of individuals'),
                (5, 'Step 5: Income verification documents and file upload'),
                ]
            
            # Check each record and determine which step is next to complete
            outFieldList = fieldsToExport+[('','','Last Modified Date'),('','','Next Step to Complete')]
            for idx,itm in enumerate(dbOut):
                
                # if itm[idFieldIdx]==131:
                #     raise Exception('breakpoint')
                
                # Iterate through fieldsToVerify until the first null is
                # found. This specifies that the step hasn't been completed.
                for stepnum,stepdesc in stepDescription:
                    if itm[[x[-1] for x in fieldsToVerify].index(stepnum)+len(fieldsToExport)] is None or itm[[x[-1] for x in fieldsToVerify].index(stepnum)+len(fieldsToExport)] is False:
                        
                        # raise Exception('breakpoint')
                        
                        # Use the 'modified' date to ensure we're not reaching
                        # out too soon
                        cursor.execute(
                            self.getfoco.select_framework.format(
                                fields='{}."{}"'.format(
                                    fieldsToCheck[stepnum-1][0],
                                    fieldsToCheck[stepnum-1][1],
                                    ),
                                wherePlaceholder='where au."id"={}'.format(
                                    itm[idFieldIdx],
                                    ),   # if not blank, must start with 'where...'
                                )
                            )
                        dtCheck = cursor.fetchone()[0]
                        
                        # Set the record to None to be removed later if it's
                        # been modified recently
                        if dtCheck >= pendulum.now().subtract(days=5):
                            dbOut[idx] = [None]*(len(itm)+2)
                        else:
                            dbOut[idx] = list(itm)+[dtCheck.strftime('%Y-%m-%d'),stepdesc]
                        break
                        
                else:
                    raise Exception(
                        "This element may have been included in the 'incomplete' list by accident:\nIndex: {}\n{}".format(
                            idx,
                            itm,
                            )
                        )

        else:
            dbOut = []
            
        dbExtract = [[x[fdidx] for fdidx in range(len(fieldsToExport))]+x[-2:] for x in dbOut]
                    
        ## Account for income-verified but no programs applied for
        fieldList = ','.join(
                [f'{x[0]}."{x[1]}"' for x in fieldsToExport]
                )
        
        whereClause = """ where au."is_archived"=false"""
            
        # Append to where clause so that only qualified and verified
        # applicants appear
        whereClause+=""" and ae."GenericQualified"='ACTIVE'"""
        
        # Check for any user that has *only* empty string for qualified
        # programs (e.g. programs that they are eligible for)
        
        # qualFieldsToCheck is ('table', 'field', 'ami threshold')
        qualFieldsToCheck = [
            ('ae', 'GRqualified', 0.60),
            ('ae', 'RecreationQualified', 0.30),
            ('ae', 'ConnexionQualified', 0.60),
            ('ae', 'SPINQualified', 0.30),
            ]   
        # whereClause+=""" and {}""".format(
        #     ' and '.join(
        #         [f'{x[0]}."{x[1]}" is NULL' for x in qualFieldsToCheck]
        #         )
        #     )
        # whereClause+=""" and {}""".format(
        #     ' and '.join(
        #         [f"""{x[0]}."{x[1]}"!='ACTIVE'""" for x in qualFieldsToCheck]+[f"""{x[0]}."{x[1]}"!='PENDING'""" for x in qualFieldsToCheck]+[f"""{x[0]}."{x[1]}"!='NOTQUALIFIED'""" for x in qualFieldsToCheck]
        #         )
        #     )
        
        # Use CASE..WHEN so that each AND'd statement is True if the user
        # doesn't qualify (effectively excluded from the AND)
        # e.g.
        # case
        #   when ae."AmiRange_max"<=0.6 then ae."GRqualified"=''
        #   else true
        # end
        
        # The corner case for this is if all CASEs are False, leading to the
        # user being included in the query because they don't qualify for any
        # programs...but that shouldn't be possible because of the
        # GenericQualified='ACTIVE' check        
        whereClause+=""" and {}""".format(
            ' and '.join(
                [f"""case when {x[0]}."AmiRange_max"<={x[2]} then {x[0]}."{x[1]}"='' else true end""" for x in qualFieldsToCheck]
                )
            )
        
        # Filter out all IDs that are in dbOut
        if len(dbOut)>0:
            whereClause+=""" and au."id" not in ({})""".format(
                ','.join([str(x[idFieldIdx]) for x in dbOut if x[idFieldIdx] is not None])
                )
            
        queryStr = self.getfoco.select_framework.format(
            fields=fieldList,
            wherePlaceholder=whereClause,   # if not blank, must start with 'where...'
            )    
            
        cursor.execute(queryStr)
        dbOut = cursor.fetchall()
        
        if len(dbOut)>0:
            # Add 'Next Step to Complete' as 'Apply for a program'
            for idx,itm in enumerate(dbOut):
                dbOut[idx] = list(itm)+['','Dashboard: Have not applied for a program']
                
            dbExtract.extend(dbOut)
                
        if len(dbExtract)>0:
            # Convert to dataframe
            df = self.getfoco._convert_extract(
                [x[2] for x in outFieldList],
                dbExtract,
                )
                
            # These don't seem to be necessary anymore
            
            # # Remove records that are all None values
            # dbSchema.tI(0).removeNullRecords()
            
            # # Sort by ID ascending
            # dbSchema.tI(0).sortFieldsBy('primary_id')
            
            # Write to file
            df.to_csv(
                os.path.join(
                    self.getfoco.output_file_dir,
                    '{dt} {prg}'.format(
                        dt=pendulum.now().date(),
                        prg='Incomplete IQ Applications.csv',
                        )
                    ),
                index=False,
                )
            
        cursor.close()
        
    def export_feedback(
            self,
            save_file: bool = True,
            save_dir: Union[str, Path] = None,
            ) -> None:
        """
        Export user feedback from the dashboard. This is separate because
        the feedback isn't linked to a user.

        Parameters
        ----------
        save_file : bool, optional
            Save the file (rather than just run the calculations in memory).
            The default is True.
        save_dir : Union[str, Path], optional
            Directory to save the file. The default is 
            self.getfoco.output_file_dir.

        Returns
        -------
        None

        """
        
        if self.getfoco.conn.closed == 1:
            self.getfoco._connect()
        
        cursor = self.getfoco.conn.cursor()
        
        # Call out feedback fields
        fieldList = [
            ('fb','modified','Date'),
            ('fb','star_rating',"Rating (of 5 stars)"),
            ('fb','feedback_comments','Comments'),
            ]
        queryStr = "select {fd} from public.app_feedback as fb".format(
            fd=','.join(
                [f'{x[0]}."{x[1]}"' for x in fieldList]
                ),
            )    
            
        cursor.execute(queryStr)
        dbOut = cursor.fetchall()
        
        # Convert to dataframe
        df = self.getfoco._convert_extract(
            [x[2] for x in fieldList],
            dbOut,
            )
        
        # Convert timestamps to Denver timezone and user-friendly format
        df['Date'] = df[['Date']].applymap(
            lambda x: x.tz_convert(tz='America/Denver').strftime('%Y-%m-%d %X')
            )
            
        if save_file:
            # Define save_path if not explicitly stated
            if save_dir is None:
                save_dir = self.getfoco.output_file_dir
            else:
                save_dir = Path(save_dir)
                
            save_path = save_dir.joinpath(
                '{dt} IQ Feedback.csv'.format(
                    dt=pendulum.now().date(),
                    ),
                )
                
            # Write to file
            df.to_csv(
                save_path,
                index=False,
                )
    
            print("Extract saved!")
        
        cursor.close()

    def removeIdsWithRenewalIssues(self, userIds):
        newList = []
        # userIds = self.getUserIds(queryset)
        for userId in userIds:
            accountWithIssues = list(IQProgram.objects.values(
                    'user_id',
                    'program_id'
                ).annotate(
                    count=Count('*')
                ).filter(
                    user_id=userId,
                    count__gt=1
                ))
            
            if len(accountWithIssues):
                newList.append(accountWithIssues[0]['user_id'])
                # userIds.remove(accountWithIssues[0][0])

        cleanedUserIds = [id for id in userIds if id not in newList]

        return cleanedUserIds
    
    def getUserIds(self, queryset):
        userIds = []
        for item in queryset:
            userIds.append(item)
        