from app import models

import random


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

        program_info = {
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

        # Create EligibilityProgramRD records, if they don't already exist

        for prgname, prgvals in program_info.items():
            exist_count = models.EligibilityProgramRD.objects.filter(
                program_name=prgname
            ).count()

            # If a record DNE, create one
            if exist_count == 0:
                models.EligibilityProgramRD.objects.create(
                    program_name=prgname,
                    **prgvals,
                )

        # Create EligibilityProgram records

        self.eligibility = []
        for prgname in program_info.keys():
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

        program_info = {
            'grocery': {
                'ami_threshold': 0.6,
                'friendly_name': 'Grocery Tax Rebate',
                'friendly_category': 'Food Assistance',
                'friendly_description': 'The Grocery Rebate Tax is an annual cash payment to low-income individuals and families living in the City of Fort Collins and its Growth Management Area. It provides your family with direct assistance in exchange for the taxes you spend on food.',
                'friendly_supplemental_info': 'Applications accepted all year',
                'learn_more_link': 'https://www.fcgov.com/rebate/',
                'friendly_eligibility_review_period': 'Estimated Notification Time: Two Weeks',
                'is_active': True,
            },
            'connexion': {
                'ami_threshold': 0.6,
                'friendly_name': 'Reduced-Rate Connexion',
                'friendly_category': 'Connexion Assistance',
                'friendly_description': 'As Connexion comes online in neighborhoods across our community, the City of Fort Collins is committed to fast, affordable internet. Digital Access & Equity is an income-qualified rate of $20 per month for 1 gig-speed of internet plus wireless.',
                'friendly_supplemental_info': 'Applications accepted all year',
                'learn_more_link': 'https://fcconnexion.com/digital-inclusion-program/',
                'friendly_eligibility_review_period': 'Estimated Notification Time: Two Weeks',
                'is_active': True,
            },
        }

        # Create IQProgramRD records, if they don't already exist

        for prgname, prgvals in program_info.items():
            exist_count = models.IQProgramRD.objects.filter(
                program_name=prgname
            ).count()

            # If a record DNE, create it
            if exist_count == 0:
                models.IQProgramRD.objects.create(
                    program_name=prgname,
                    **prgvals,
                )

        # Create IQProgram records

        self.iq = []
        for prgname in program_info.keys():
            self.iq.append(
                models.IQProgram.objects.create(
                    user=self.user,
                    program=models.IQProgramRD.objects.get(program_name=prgname),
                    is_enrolled=False,
                    has_renewed=True,
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