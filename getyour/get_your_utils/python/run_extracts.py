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
import re
from tomlkit import loads
from pathlib import Path
from typing import Union
import pandas as pd
from fnmatch import fnmatch

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import print

from django.db.models import Count
from app import models
from app.models import IQProgramRD, IQProgram, User, HouseholdMembersHist

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
        self.kwargs = kwargs

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

        self.output_file_dir = fileDir
        
        # with open(
        #         fileDir.parent.parent.joinpath('.env.deploy'),
        #         'r',
        #         encoding='utf-8',
        #         ) as f:
        #     secrets_dict = loads(f.read())
            
        # for key in secrets_dict.keys():
        #     setattr(self, key, secrets_dict[key])
            
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

            valueListFields = ['is_updated', 'householdmembers__is_updated', 'address__is_updated']

            if (len(tableCheckList) == 1 and 'u' in tableCheckList):
                valueListFields = ['id', 'first_name', 'last_name', 'email']
            #TODO: need to figure out if this will work.  Not sure if [0], at the end, will be needed
            tableCheckOut = list(User.objects.select_related(
                'householdmembers',
                'household',
                'address__mailing_address'
            ).filter(
                is_archived=False,
                id=itm[idFieldIdx] # user id in list
            ).values_list(
                *valueListFields
            ))[0]
            
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

                    histQuerySet = modelClass.objects.filter(
                        user_id=itm[idFieldIdx]
                    ).values(
                        tableRef[2]
                    ).order_by(
                        '-id'
                    ).first()['historical_values']
                    
                    if histQuerySet is not None:
                        histOut = histQuerySet['historical_values']
                    else:
                        if modelName == 'AddressHist':
                            histOut = {"mailing_address_id": 0, "eligibility_address_id": 0}
                        else:
                            histOut = {}
                    
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
                            '-created'
                        ).first()
                    
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
                    # TODO: write this to a buffer instead 
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
                        iqprogramRecord = IQProgram.objects.filter(
                            user_id=id,
                            program_id=programId
                        ).get()
                        # iqprogramRecord.is_enrolled = True
                        # iqprogramRecord.enrolled_at = pendulum.now()
                        # iqprogramRecord.save()
                    
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
            
        else:
            print("Update designations in the database were not reset")

        return [x for x in self.output_file_dir.iterdir() if x.name.startswith(str(pendulum.today().year))]
        