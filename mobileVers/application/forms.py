# All of the forms built from models are here 
from django import forms

from .models import User, Addresses, Eligibility, programs

# form for user account creation
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['firstName','lastName', 'email', 'password']
        labels  = { 
            'firstName':'First Name', 
            'lastName':'Last Name', 
            'password':'Password', 
            'email':'Email',
            # TODO:@Grace check this and implement? 
            # 'phone':'Phone',
        }

# form for addresses
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

# form for basic finance eligibility
class EligibilityForm(forms.ModelForm):
    class Meta:
        model = Eligibility
        fields = ['rent', 'dependents', 'grossAnnualHouseholdIncome']
        labels  = { 
            'rent':'Rent',
            'dependents':'Number of Dependents', 
            'grossAnnualHouseholdIncome':'Gross Annual Household Income',
        } 

# programs they are available for
class programForm(forms.ModelForm):
    class Meta:
        model = programs
        fields = ['snap', 'freeReducedLunch',]
        labels  = { 
            'snap':'SNAP',
            'freeReducedLunch':'Free and Reduced Lunch', 
        } 
        