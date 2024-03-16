"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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
from app import models

import random
import pendulum


class CreateEligibilityPrograms:

    def __init__(self):
        """
        Define Eligibility Programs to use in testing.
        
        """

        self.program_info = {
            'snap': {
                'ami_threshold': 0.3,
                'friendly_name': 'Supplemental Nutrition Assistance Program (SNAP)',
                'friendly_description': 'SNAP Card',
                'is_active': True,
            },
            'chp': {
                'ami_threshold': 0.6,
                'friendly_name': 'Child Health Plan Plus (CHP+)',
                'friendly_description': 'Colorado Child Health Plan Plus (CHP+) card',
                'is_active': True,
            },
        }

        self.create_programs()

    def create_programs(self):
        """
        Create EligibilityProgramRD records, if they don't already exist.

        """

        for prgname, prgvals in self.program_info.items():
            exist_count = models.EligibilityProgramRD.objects.filter(
                program_name=prgname
            ).count()

            # If a record DNE, create one
            if exist_count == 0:
                models.EligibilityProgramRD.objects.create(
                    program_name=prgname,
                    **prgvals,
                )


class CreateIqPrograms:

    def __init__(self):
        """
        Define IQ Programs for use in testing.
        
        """

        self.program_info = {
            'iqprogram_0': {
                'ami_threshold': 0.6,
                'friendly_name': 'IQ Program 0',
                'friendly_category': 'Food Assistance',
                'friendly_description': 'This is the first IQ Program in the catalog.',
                'friendly_supplemental_info': 'Applications accepted all year',
                'learn_more_link': 'https://github.com/Get-Your/Get-Your',
                'friendly_eligibility_review_period': 'Estimated Notification Time: Two Weeks',
                'is_active': True,
                'renewal_interval_year': 1,
            },
            'iqprogram_1': {
                'ami_threshold': 0.3,
                'friendly_name': 'IQ Program 1',
                'friendly_category': 'Utility Assistance',
                'friendly_description': 'This is the second IQ Program in the catalog.',
                'friendly_supplemental_info': 'Applications accepted all year',
                'learn_more_link': 'https://github.com/Get-Your/Get-Your',
                'friendly_eligibility_review_period': 'Estimated Notification Time: Two Weeks',
                'is_active': True,
            },
        }

        self.create_programs()

    def create_programs(self):
        """
        Create IQProgramRD records, if they don't already exist.

        """

        for prgname, prgvals in self.program_info.items():
            exist_count = models.IQProgramRD.objects.filter(
                program_name=prgname
            ).count()

            # If a record DNE, create it
            if exist_count == 0:
                models.IQProgramRD.objects.create(
                    program_name=prgname,
                    **prgvals,
                )


class TestUser:

    def __init__(
            self,
            use_gma_address: bool = True,
            use_verified_income: bool = True,
            ):
        """
        Create a fully-validated test user with a random email address.
         
        Multiple users can be created for one test.
        
        """

        self.use_gma_address = use_gma_address
        self.use_verified_income = use_verified_income

        self.create_user()
        self.create_address()
        self.create_household()
        self.create_eligibility()
        self.create_iq()


    def create_user(self):
        """ Create user record. """

        pword = 'Something top secret'
        
        self.user = models.User.objects.create_user(
            email=f"test_user_{random.randint(1,100000)}@ae.ae",
            first_name='Test',
            last_name='User',
            phone_number='+13035551234',
            password=pword,
            has_viewed_dashboard=False,
            # Mark is_archived as a fallback in case tearDown() fails
            is_archived=True,
            is_updated=False,
            last_completed_at=pendulum.now(),
        )

        self.user.plaintext_password = pword


    def create_address(self):
        """ Create address record (in each table, if applicable). """

        # Create AddressRD record

        if self.use_gma_address:
            # For a GMA address, use Fort Collins City Hall
            address_info = {
                'address1': '300 LAPORTE AVE',
                'address2': '',
                'city': 'FORT COLLINS',
                'state': 'CO',
                'zip_code': 80521,
                'is_in_gma': True,
                'is_city_covered': True,
                'has_connexion': True,
                'is_verified': True,
            }
        else:
            # For a non-GMA address, use Cottonwood Plains Elementary School
            address_info = {
                'address1': '525 TURMAN DR',
                'address2': '',
                'city': 'FORT COLLINS',
                'state': 'CO',
                'zip_code': 80525,
                'is_in_gma': False,
                'is_city_covered': False,
                'has_connexion': False,
                'is_verified': True,
            }

        # Since these are in already-cleaned format, search based on unique
        # address
        exist_count = models.AddressRD.objects.filter(
            **address_info
        ).count()

        # If a record exists, get it; else, create one
        if exist_count > 0:
            self.addressrd = models.AddressRD.objects.get(
                **address_info
            )
        else:
            self.addressrd = models.AddressRD(
                **address_info
            )
            # Clean the field values (which adds the hash as well), then save
            self.addressrd.clean()
            self.addressrd.save()

        # Create Address record

        self.address = models.Address.objects.create(
            user=self.user,
            mailing_address=self.addressrd,
            eligibility_address=self.addressrd,
        )
        
        
    def create_household(self):
        """ Create all household information. """

        self.household = models.Household.objects.create(
            user=self.user,
            duration_at_address='Less than a year',
            number_persons_in_household=1,
            income_as_fraction_of_ami=0.3,
            is_income_verified=self.use_verified_income,
            rent_own='rent',
        )

        self.householdmembers = models.HouseholdMembers.objects.create(
            user=self.user,
            household_info={
                'this': 'some fake JSON, for now',
            }
        )


    def create_eligibility(self):
        """ Create Eligibility Program record(s). """

        program_rd = CreateEligibilityPrograms()

        self.eligibility = []
        for prgname in program_rd.program_info.keys():
            # Note that these will have blank document_path values
            self.eligibility.append(
                models.EligibilityProgram.objects.create(
                    user=self.user,
                    program=models.EligibilityProgramRD.objects.get(program_name=prgname),
                    document_path=[],
                )
            )


    def create_iq(self):
        """ Create IQ Program record(s). """

        program_rd = CreateIqPrograms()

        self.iq = []
        for prgname in program_rd.program_info.keys():
            self.iq.append(
                models.IQProgram.objects.create(
                    user=self.user,
                    program=models.IQProgramRD.objects.get(program_name=prgname),
                    is_enrolled=False,
                )
            )


    def destroy(self):
        """ Destroy the user (e.g. once the test is complete). """

        models.User.objects.filter(id=self.user.id).delete()


class TestView:

    def __init__(self):
        """
        Set parameters for views to be tested.
         
        The first 'views' test is to ensure all views are accounted for.
        
        """

        self.required_keys = [
            'login_required',
            'direct_access_allowed',
        ]

        self.named_app_views = {
            'index': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'quick_available': {
                'login_required': False,
                'direct_access_allowed': False,
            },
            'quick_not_available': {
                'login_required': False,
                'direct_access_allowed': False,
            },
            'quick_coming_soon': {
                'login_required': False,
                'direct_access_allowed': False,
            },
            'quick_not_found': {
                'login_required': False,
                'direct_access_allowed': False,
            },
            'programs_info': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'privacy_policy': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'address': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'account': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'household': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'household_members': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'programs': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'address_correction': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'take_usps_address': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'household_definition': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'get_ready': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'files': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'broadcast': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'notify_remaining': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'quick_apply': {
                'login_required': True,
                'direct_access_allowed': False,
                'kwargs': {'iq_program': 'grocery'},
            },
            'feedback': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'feedback_received': {
                'login_required': True,
                'direct_access_allowed': False,
            },
            'dashboard': {
                'login_required': True,
                'direct_access_allowed': True,
            },
            'qualified_programs': {
                'login_required': True,
                'direct_access_allowed': True,
            },
            'programs_list': {
                'login_required': True,
                'direct_access_allowed': True,
            },
            'user_settings': {
                'login_required': True,
                'direct_access_allowed': True,
            },
            'privacy': {
                'login_required': True,
                'direct_access_allowed': True,
            },
            'login': {
                'login_required': False,
                'direct_access_allowed': True,
            },
            'password_reset': {
                'login_required': False,
                'direct_access_allowed': False,
            },
        }

        self.process_values()

    def process_values(self):
        """ Sort lists by name, where applicable. """

        self.required_keys.sort()
