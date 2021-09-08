# All of the forms built from models are here 
from django import forms

from .models import User, Addresses, Eligibility, programs, choices, addressLookup, futureEmails, attestations

# form for user account creation
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name','last_name', 'email', 'password','phone_number']
        labels  = { 
            'first_name':'First Name', 
            'last_name':'Last Name', 
            'password':'Password', 
            'email':'Email',
            'phone_number':'Phone Number',
        }
    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        user.set_password(user.password) # set password properly before commit
        if commit:
            user.save()
        return user

# form for addresses
class AddressForm(forms.ModelForm):
    class Meta:
        model = Addresses
        fields = ['address', 'address2', 'city', 'state', 'zipCode']
        labels  = { 
            'user_id': 'user_id',
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
        fields = ['rent','dependents', 'grossAnnualHouseholdIncome']
        labels  = {
            'rent':'Rent',
            'dependents':'Number of Dependents', 
            'grossAnnualHouseholdIncome':'Adjusted Gross Annual Household Income',
        } 

# form for basic finance eligibility
class EligibilityFormPlus(forms.ModelForm):
    class Meta:
        model = Eligibility
        fields = ['dependentsAge',]
        labels  = {
            'dependentsAge':'Age of Dependents', 
        } 


# programs they are available for
class programForm(forms.ModelForm):
    class Meta:
        model = programs
        fields = ['snap', 'freeReducedLunch', 'Identification']
        labels  = { 
            'snap':'Food Assistance (SNAP)',
            'freeReducedLunch':'Free and Reduced Lunch',
            'Identification':'Identification Card',
        } 

class attestationForm(forms.ModelForm):
    class Meta:
        model = attestations
        fields = ['localAttestation', 'completeAttestation',]
        labels  = { 
            'localAttestation':'I am lawfully present in the United States and/or am ONLY applying on behalf on my children (under 18 years of age) who are lawfully present.',
            'completeAttestation':'I verify the information stated on this application is true.',
        } 

class addressLookupForm(forms.ModelForm):
    class Meta:
        model = addressLookup
        fields = ['address']
        labels  = { 
            'address':'Address', 
        } 

class futureEmailsForm(forms.ModelForm):
    class Meta:
        model = futureEmails
        fields = ['email', 'connexionCommunication']
        labels  = { 
            'email':'Email Address', 
            'connexionCommunication':'By checking this box, I agree to receive communications from Fort Collins Connexion. I understand I may opt out at any time.'
        } 