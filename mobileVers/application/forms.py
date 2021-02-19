# All of the forms built from models are here 
from django import forms

from .models import User, Addresses, Eligibility, programs

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['firstName','lastName', 'email', 'password']
        labels  = { 
            'firstName':'First Name', 
            'lastName':'Last Name', 
            'password':'Password', 
            'email':'Email',
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Addresses
        fields = ['address', 'address2', 'city', 'state', 'zipCode', 'n2n']
        labels  = { 
            'address':'Address',
            'address2':'Apt, Suite, etc', 
            'city':'City', 
            'state':'State', 
            'zipCode':'Zip Code',
        }

class EligibilityForm(forms.ModelForm):
    class Meta:
        model = Eligibility
        fields = ['rent', 'dependents', 'grossAnnualHouseholdIncome']
        labels  = { 
            'rent':'Rent',
            'dependents':'Number of Dependents', 
            'grossAnnualHouseholdIncome':'Gross Annual Household Income',
        } 

class programForm(forms.ModelForm):
    class Meta:
        model = programs
        fields = ['snap', 'freeReducedLunch',]
        labels  = { 
            'snap':'SNAP',
            'freeReducedLunch':'Free and Reduced Lunch', 
        } 
        