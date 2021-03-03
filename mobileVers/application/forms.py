# All of the forms built from models are here 
from django import forms

from .models import User, Addresses, Eligibility, programs, choices

# form for user account creation
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['firstName','lastName', 'email', 'password','phone_number']
        labels  = { 
            'firstName':'First Name', 
            'lastName':'Last Name', 
            'password':'Password', 
            'email':'Email',
            'phone_number':'Phone Number',
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
    rent = forms.ChoiceField(choices=choices,widget=forms.RadioSelect(),label="Rent")
    class Meta:
        model = Eligibility
        fields = ['dependents', 'grossAnnualHouseholdIncome']
        labels  = {
            'dependents':'Number of Dependents', 
            'grossAnnualHouseholdIncome':'Gross Annual Household Income',
        } 

# programs they are available for
class programForm(forms.ModelForm):
    class Meta:
        model = programs
        fields = ['snap', 'freeReducedLunch',]
        labels  = { 
            'snap':'Food Assistance (SNAP)',
            'freeReducedLunch':'Free and Reduced Lunch', 
        } 
        