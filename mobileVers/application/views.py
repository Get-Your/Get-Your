from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, logout

from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from .forms import UserForm, AddressForm, EligibilityForm, programForm, addressLookupForm, futureEmailsForm, EligibilityFormPlus,attestationForm
from .backend import addressCheck, validateUSPS, qualification
from django.http import QueryDict

from py_models.qualification_status import QualificationStatus

import logging
import usaddress


formPageNum = 6

# first index page we come into
def index(request):
    
    if request.method == "POST": 
        form = addressLookupForm(request.POST or None)
        if form.is_valid():
            try:
                form.save()
                
                # Use usaddress to try to parse the input text into an address
                
                # Clean the data
                # Remove 'fort collins' - the multi-word city can confuse the
                # parser
                addressStr = form.cleaned_data['address'].lower().replace('fort collins','')
                
                # Use the following tag mapping for USPS standards
                tag_mapping = {
                   'Recipient': 'recipient',
                   'AddressNumber': 'address_2',
                   'AddressNumberPrefix': 'address_2',
                   'AddressNumberSuffix': 'address_2',
                   'StreetName': 'address_2',
                   'StreetNamePreDirectional': 'address_2',
                   'StreetNamePreModifier': 'address_2',
                   'StreetNamePreType': 'address_2',
                   'StreetNamePostDirectional': 'address_2',
                   'StreetNamePostModifier': 'address_2',
                   'StreetNamePostType': 'address_2',
                   'CornerOf': 'address_2',
                   'IntersectionSeparator': 'address_2',
                   'LandmarkName': 'address_2',
                   'USPSBoxGroupID': 'address_2',
                   'USPSBoxGroupType': 'address_2',
                   'USPSBoxID': 'address_2',
                   'USPSBoxType': 'address_2',
                   'BuildingName': 'address_1',
                   'OccupancyType': 'address_1',
                   'OccupancyIdentifier': 'address_1',
                   'SubaddressIdentifier': 'address_1',
                   'SubaddressType': 'address_1',
                   'PlaceName': 'city',
                   'StateName': 'state',
                   'ZipCode': 'zipcode',
                }
                
                rawAddressDict, addressType = usaddress.tag(
                    addressStr,
                    tag_mapping,
                    )
                
                # Only continue to validation, etc if a 'Street Address' is
                # found by usaddress
                if addressType != 'Street Address':
                    raise NameError("The address cannot be parsed")
                    
                print(
                    'Address parsing found',
                    rawAddressDict,
                    )
                
                # Help out parsing with educated guesses
                # if 'state' not in rawAddressDict.keys():
                rawAddressDict['state'] = 'CO'
                # if 'city' not in rawAddressDict.keys():
                rawAddressDict['city'] = 'Fort Collins'
                    
                print(
                    'Updated address parsing is', 
                    rawAddressDict,
                    )
                    
                # Ensure the necessary keys for USPS validation are included
                uspsKeys = [
                    'name',
                    'address_1',
                    'address_2',
                    'city',
                    'state',
                    'zipcode']
                rawAddressDict.update(
                    {key:'' for key in uspsKeys if key not in rawAddressDict.keys()}
                    )
                
                # Validate to USPS address
                addressDict = validateUSPS(rawAddressDict)
                
                # Check for IQ and Connexion services
                isInGMA, hasConnexion = addressCheck(addressDict)
                
                if isInGMA:
                    # Connexion status unknown, but since isInGMA==True, it
                    # will be available at some point
                    if not hasConnexion:    # this covers both None and False
                        return redirect(reverse("application:quickComingSoon"))
                        
                    else:  # hasConnexion==True is the only remaining option
                        return redirect(reverse("application:quickAvailable"))
                    
                else:
                    return redirect(reverse("application:quickNotAvailable"))

            except:
                #TODO implement look into logs!
                logging.warning("insert valid zipcode")
                return(redirect(reverse("application:quickNotFound")))
    
    form = addressLookupForm() 
    logout(request)
    return render(request, 'application/index.html', {
            'form':form,
        })

def address(request):

    if request.method == "POST": 
        try:
            existing = request.user.addresses
            form = AddressForm(request.POST,instance = existing)
        except ObjectDoesNotExist:
            form = AddressForm(request.POST or None)

        print(form.data)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user_id = request.user

            instance.save()            
            return redirect(reverse("application:addressCorrection"))
    else:
        form = AddressForm()

    return render(request, 'application/address.html', {
        'form':form,
        'step':2,
        'request.user':request.user,
        'formPageNum':formPageNum,
        })


def addressCorrection(request):
    try:
        q = QueryDict('', mutable=True)
        q.update({"address": request.user.addresses.address, 
            "address2": request.user.addresses.address2, 
            "city": request.user.addresses.city,
            "state": request.user.addresses.state,
            "zipcode": str(request.user.addresses.zipCode),})
        dict_address = validateUSPS(q)
        print(dict_address['AddressValidateResponse']['Address'])
        program_string_2 = [dict_address['AddressValidateResponse']['Address']['Address2'], 
                            dict_address['AddressValidateResponse']['Address']['Address1'],
                            dict_address['AddressValidateResponse']['Address']['City'] + " "+ dict_address['AddressValidateResponse']['Address']['State'] +" "+  str(dict_address['AddressValidateResponse']['Address']['Zip5'])]
    except TypeError or RelatedObjectDoesNotExist:
        program_string_2 = ["Sorry, we couldn't verify this address through USPS."]
        print("USPS couldn't figure it out!")
    program_string = [request.user.addresses.address, request.user.addresses.address2, request.user.addresses.city + " " + request.user.addresses.state + " " + str(request.user.addresses.zipCode)]
    return render(request, 'application/addressCorrection.html',  {
        'step':2,
        'formPageNum':formPageNum,
        'program_string': program_string,
        'program_string_2': program_string_2,
    })

def takeUSPSaddress(request):
    try:
        q = QueryDict('', mutable=True)
        q.update({"address": request.user.addresses.address, 
            "address2": request.user.addresses.address2, 
            "city": request.user.addresses.city,
            "state": request.user.addresses.state,
            "zipcode": str(request.user.addresses.zipCode),})
        dict_address = validateUSPS(q)
        
        # Check for and store GMA and Connexion status
        isInGMA, hasConnexion = addressCheck(dict_address)

        instance = request.user.addresses
        instance.user_id = request.user
        instance.address = dict_address['AddressValidateResponse']['Address']['Address2']
        instance.address2 = dict_address['AddressValidateResponse']['Address']['Address1']
        instance.city = dict_address['AddressValidateResponse']['Address']['City']
        instance.state = dict_address['AddressValidateResponse']['Address']['State']
        instance.zipCode = int(dict_address['AddressValidateResponse']['Address']['Zip5'])
        
        instance.isInGMA = isInGMA
        instance.hasConnexion = hasConnexion
        
        instance.save()
    except TypeError or RelatedObjectDoesNotExist:
        print("USPS couldn't figure it out!")

    return redirect(reverse("application:inServiceArea"))



def inServiceArea(request):
    if request.user.addresses.isInGMA:
        return redirect(reverse("application:finances")) #TODO figure out to clean?
    else:
        print("address not in GMA")
        return redirect(reverse("application:notAvailable")) 


def account(request):
    if request.method == "POST": 
        # maybe also do some password requirements here too
        try:
            existing = request.user
            form = UserForm(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = UserForm(request.POST or None)
        if form.is_valid():
            # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
            # Make sure password isn't getting saved twice
            print(form.data)
            try:
                user = form.save()
                login(request,user)
                print("userloggedin")
            except AttributeError:
                print("user error, login not saved, user is: " + str(user))
            return redirect(reverse("application:address"))
    else:
        form = UserForm()

    return render(request, 'application/account.html', {
    'form':form,
    'step':1,
    'formPageNum':formPageNum,
    })
#    else:
#        return redirect(reverse(page))

def moreInfoNeeded(request):
    if request.method =="POST":
        try:
            existing = request.user.eligibility
            form = EligibilityFormPlus(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = EligibilityFormPlus(request.POST or None)
        if form.is_valid():
            print(form.data)
            instance = form.save
            instance.user_id = request.user
        
            print("SAVING")
            instance.save()
            # If DEqualified is not blank (either PENDING or ACTIVE),
            # go to the financial information page
            if instance.DEqualified == QualificationStatus.PENDING.name or instance.DEqualified == QualificationStatus.ACTIVE.name:
                    return redirect(reverse("application:mayQualify"))
            else:
                    return redirect(reverse("application:programs"))
        else:
            print(form.data)
    else:
        form = EligibilityFormPlus()
     
    return render(request, "application/moreInfoNeeded.html",{
        'step':2,
        'dependent':request.user.eligibility.dependents,
        'list':list(range(request.user.eligibility.dependents)),
        'formPageNum':3,
    })

def finances(request):
    if request.method == "POST":
        try:
            existing = request.user.eligibility
            form = EligibilityForm(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = EligibilityForm(request.POST or None)
        if form.is_valid():
            print(form.data)
            instance = form.save(commit=False)
            instance.user_id = request.user       
            #take dependent information, compare that AMI level number with the client's income selection and determine if qualified or not, flag this
            if form['grossAnnualHouseholdIncome'].value() == 'Below $19,800':
                print("GAHI is below 19,800")
                if qualification(form['dependents'].value(),) >= 19800:
                    # Set to 'PENDING' (for pending enrollment). Never set to 
                    # 'ACTIVE' from Django
                    instance.DEqualified = QualificationStatus.PENDING.name
                else:
                    instance.DEqualified = QualificationStatus.NOTQUALIFIED.name
            elif form['grossAnnualHouseholdIncome'].value() == '$19,800 ~ $32,800':
                print("GAHI is between 19,800 and 32,800")
                if 19800 <= qualification(form['dependents'].value(),) <= 32800:
                    # Set to 'PENDING' (for pending enrollment). Never set to 
                    # 'ACTIVE' from Django
                    instance.DEqualified = QualificationStatus.PENDING.name
                else:
                    instance.DEqualified = QualificationStatus.NOTQUALIFIED.name
            elif form['grossAnnualHouseholdIncome'].value() == 'Over $32,800':
                print("GAHI is above 32,800")
                if qualification(form['dependents'].value(),) >= 32800:
                    # Set to 'PENDING' (for pending enrollment). Never set to 
                    # 'ACTIVE' from Django
                    instance.DEqualified = QualificationStatus.PENDING.name
                else:
                    instance.DEqualified = QualificationStatus.NOTQUALIFIED.name                      
                
            print("SAVING")
            instance.save()
            # If DEqualified is not blank (either PENDING or ACTIVE),
            # go to the financial information page
            if instance.DEqualified == QualificationStatus.PENDING.name or instance.DEqualified == QualificationStatus.ACTIVE.name:
                return redirect(reverse("application:mayQualify"))
            else:
                return redirect(reverse("application:programs"))
        else:
            print(form.data)
    else:
        form = EligibilityForm()

    return render(request, 'application/finances.html', {
        'form':form,
        'step':3,
        'formPageNum':formPageNum,
    })


def GRQuickApply(request):
    obj = request.user.eligibility
    print(obj.GRqualified)
    #print(request.user.eligibility.GRQualified)
    obj.GRqualified = QualificationStatus.PENDING.name
    print(obj.GRqualified)
    obj.save()
    return render(request, "application/GRQuickApply.html",)

def RecreationQuickApply(request):
    obj = request.user.eligibility
    print(obj.RecreationQualified)
    #print(request.user.eligibility.GRQualified)
    obj.RecreationQualified = QualificationStatus.PENDING.name
    print(obj.RecreationQualified)
    obj.save()
    return render(request, "application/RecreationQuickApply.html",)


def attestation(request):
    if request.method == "POST": 
        try:
            existing = request.user.attestations
            form = attestationForm(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = attestationForm(request.POST or None)
        if form.is_valid():
            print(form.data)
            print(request.session)
            try:
                instance = form.save(commit=False)
                instance.user_id = request.user
                instance.save()
                return redirect(reverse("dashboard:broadcast"))
            except IntegrityError:
                print("User already has information filled out for this section")
            return redirect(reverse("application:available"))
    else:
        form = attestationForm()

    return render(request, "application/attestation.html",{
        'form':form,
        'step':6,
        'formPageNum':formPageNum,
    })



def programs(request):
    if request.method == "POST": 
        try:
            existing = request.user.programs
            form = programForm(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = programForm(request.POST or None)
        if form.is_valid():
            print(form.data)
            print(request.session)
            try:
                instance = form.save(commit=False)
                instance.user_id = request.user
                instance.save()
                return redirect(reverse("dashboard:files"))
            except IntegrityError:
                print("User already has information filled out for this section")
            #enter upload code here for client to upload images
            return redirect(reverse("application:available"))
    else:
        form = programForm()

    return render(request, 'application/programs.html', {
    'form':form,
    'step':4,
    'formPageNum':formPageNum,
    })

#    else:
#        return redirect(reverse(page))
    #return render(request, 'application/programs.html',)








def notAvailable(request):
    return render(request, 'application/notAvailable.html',)

def quickAvailable(request):
    return render(request, 'application/quickAvailable.html',)

def quickNotAvailable(request):
    return render(request, 'application/quickNotAvailable.html',) 

def quickNotFound(request):
    return render(request, 'application/quickNotFound.html',) 

def quickComingSoon(request):
    
    if request.method == "POST": 
        form = futureEmailsForm(request.POST or None)
        if form.is_valid():
            try:
                form.save()
                return redirect(reverse("application:index"))
            except AttributeError:
                print("Error Email Saving")
    
    form = futureEmailsForm()
    return render(request, 'application/quickComingSoon.html', {
            'form':form,
        })

def privacyPolicy(request):
    return render(request, 'application/privacyPolicy.html',)

def dependentInfo(request):
    return render(request, 'application/dependentInfo.html',)

def mayQualify(request):
    return render(request, 'application/mayQualify.html',{
        'step':3,
        'formPageNum':formPageNum,
    })

def callUs(request):
    return render(request, 'application/callUs.html',{
        'step':3,
        'formPageNum':formPageNum,
    })

