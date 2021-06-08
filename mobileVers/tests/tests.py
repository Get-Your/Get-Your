#from mobileVers.application.models import User
from django.test import TestCase
import application.models
import dashboard.models

class SNAPTestCase(TestCase):
    def setUp(self):

        #User.objects.get(email=username)
        User.objects.create(
            #User
            email="jandrewh@outlook.com", 
            first_name="Andrew", 
            last_name="Hernandez", 
            phone_number="6503388955",
            password="1",

            #Addresses
            address="515 Crest View Avenue",
            address2="110", 
            city="Belmont", 
            state="CA", 
            zipCode="94002",
            
            #Eligibility
            choices="Rent", #('Rent', 'Rent'),
            dependents ="0",
            #DEqualified = ?
            #GRqualified = ?
            #RecreationQualified = ?
            grossAnnualHouseholdIncome = "LOW",

            #Programs
            snap = True,

            #AddressVerification ( I.E. for Recreation)
            #Identification
            #Utility
            
            #File uploads part...
            #files? 
            #address_files?
            )
    def test_Qualifications(self):
        """Find out if test case is DE qualfied"""
        Andrew = User.objects.get(email="jandrewh@outlook.com")
        self.AssertEqual(Andrew.DEqualified, "True")