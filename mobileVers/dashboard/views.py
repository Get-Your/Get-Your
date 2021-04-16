from django.shortcuts import render, redirect, reverse
from .forms import FileForm, FeedbackForm, TaxForm 

from .models import User, Form
from application.models import Eligibility

from .backend import authenticate, files_to_string, what_page
from django.contrib.auth import get_user_model, login, authenticate, logout
from application.backend import broadcast_email, broadcast_sms

from django.db import IntegrityError



# Create your views here.

# first index page we come into


def files(request):
    file_list = {"SNAP Card": request.user.programs.snap,
                # Have Reduced Lunch be last item in the list if we add more programs
                "PSD Reduced Lunch Approval Letter": request.user.programs.freeReducedLunch,
                #"1040 Tax Form": request.user.programs.Tax1040
    }
    if request.method == "POST":   
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            print(form)  
            if request.user.is_authenticated:
                instance = form.save(commit=False)
                print(instance)
                instance.user_id = request.user
                instance.save()
                
                file_upload = request.user
                file_upload.files.add(instance)

                # Check if the user needs to upload another form
                Forms = request.user.files
                checkAllForms = [not(request.user.programs.snap),not(request.user.programs.freeReducedLunch)]
                for group in Forms.all():
                    if group.document_title == "SNAP":
                        file_list["SNAP Card"] = False
                        checkAllForms[0] = True
                    if group.document_title == "Free and Reduced Lunch":
                        checkAllForms[1] = True
                        file_list["PSD Reduced Lunch Approval Letter"] = False
                    #TODO UPDATE TO TAX BELOW
                    if group.document_title == "1040 Form":
                        checkAllForms[1] = True
                        file_list["1040 Tax Form"] = False
                
                if False in checkAllForms:
                    return render(request, 'dashboard/files.html', {
                            'form':form,
                            'programs': file_list,
                            'program_string': files_to_string(file_list),
                            'step':5,
                            'formPageNum':6,
                        })
                if request.user.programs.freeReducedLunch != True and request.user.programs.snap != True:
                    return redirect(reverse("dashboard:manualVerifyIncome"))
                else:
                    return redirect(reverse("dashboard:broadcast")) 
            else:
                print("notautnehticated")
                # TODO: Change this link
                return render(request, 'dashboard/layout.html',)
    else:
        form = FileForm()
    print(file_list)
    return render(request, 'dashboard/files.html', {
    'form':form,
    'programs': file_list,
    'program_string': files_to_string(file_list),
    'step':5,
    'formPageNum':6,
    })

def broadcast(request):
    current_user = request.user
    #Andrew Twilio functions found below!
    broadcast_email(current_user.email)
    phone = str(current_user.phone_number)
    broadcast_sms(phone)      
    return render(request, 'dashboard/broadcast.html', {
            'program_string': current_user.email,
            'step':6,
            'formPageNum':6,
        })


def index(request):
    return render(request, 'dashboard/index.html',)
    #current_user = request.user
    #return render(request, 'dashboard/index.html', {
    #    'program_string':current_user.email
    #})


def login_user(request):
    if request.method == "POST":
        # Try to log in user
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(username=email, password=password)
        # Check if the authentication was successful
        if user is not None:
            login(request, user)
            
            
            # Push user to correct page
            page = what_page(request.user)
            if what_page(request.user) == "dashboard:index":
                return redirect(reverse("dashboard:index"))
            else:
                return redirect(reverse("dashboard:notifyRemaining"))

        else:
            return render(request, "dashboard/login.html", {
                "message": "Invalid username and/or password"
            })
    
    # If it turns out user is already logged in but is trying to log in again redirect to user's homepage
    if request.method == "GET" and request.user.is_authenticated:
        return redirect(reverse("dashboard:index"))

    # Just give back log in page if none of the above is true
    else:
        return render(request, "dashboard/login.html",{})

def notifyRemaining(request):    
    page = what_page(request.user)
    return render(request, "dashboard/notifyRemaining.html",{
        "next_page": page,
    })


def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            print(form.cleaned_data['starRating'])
            print(form.cleaned_data['feedbackComments'])
            return redirect(reverse("dashboard:feedbackReceived"))
        else:
            print("form is not valid")
    else:
        form = FeedbackForm()
    if request.user.eligibility.DEqualified == True:
        text = "Based on your information, you may qualify! Be on the lookout for an email or phone call."
        text2 = "Based on your information you may also qualify for the city's Grocery Rebate Tax program!"
        text3 = "By clicking on the link below, we can send your information over and quick apply for you."
        text4 = "Click here to quick apply"
        text5 = ""
        text6 = "Utilities Income-Qualified Assistance Program"
        text7 = "The Digital Equity Office is working on a timeline to respond to applications within the next two weeks."
    else:
        text = "Based on your info, you may be over the pre-tax income limit. At this time you do not qualify. If your income changes, please apply again."
        text2 = ""
        text3 = ""
        text4 = ""
        text5 = "Grocery Rebate Tax Program"
        text6 = "Utilities Income-Qualified Assistance Program"
        text7 = "The Digital Equity Office is working on a timeline to respond to applications within the next two weeks."
    
    if request.user.eligibility.GRqualified == True:
        text2 = "Thank you for quick applying for the Grocery Rebate Tax Program."
        text3 = "Expect an update within 3 weeks - check your email!"
        text4 = ""


    return render(request, 'dashboard/index.html',context={
        "program_string": text,
        "program_string2": text2,
        "program_string3": text3,
        "program_string4": text4,
        "program_string5": text5,
        "program_string6": text6,
        "program_string7": text7,
        })


def manualVerifyIncome(request):
    if request.method == "POST": 
        form = TaxForm(request.POST)
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
        else:
            form = TaxForm()
    return render(request, "dashboard/manualVerifyIncome.html", {
    'step':5,
    'formPageNum':6,
})

def feedbackReceived(request):
    return render(request, "dashboard/feedbackReceived.html",)

def underConstruction(request):
    return render(request, "dashboard/underConstruction.html",)

#no longer used down below????
def account(request):
    if request.method == "POST": 
        # Check password with Confirm Password field, 
        # maybe also do some password requirements here too
        form = UserForm(request.POST)
        if form.is_valid():
            # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
            # Make sure password isn't getting saved twice
            email(form['email'].value(),)
            print(form.data)
            form.save()
            return redirect(reverse("application:address"))
    else:
        form = UserForm()
    return render(request, 'application/account.html', {
        'form':form,
        'step':1,
        'formPageNum':formPageNum,
    })

def finances(request):
    if request.method == "POST": 
        form = EligibilityForm(request.POST)
        if form.is_valid():
            print(form.data)
            form.save()
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

def programs(request):
    if request.method == "POST": 
        form = programForm(request.POST)
        if form.is_valid():
            print(form.data)
            form.save()
            return redirect(reverse("application:available"))
    else:
        form = programForm()
    return render(request, 'application/programs.html', {
        'form':form,
        'step':4,
        'formPageNum':formPageNum,
    })
    #return render(request, 'application/programs.html',)

def available(request):
    return render(request, 'application/de_available.html',)

def notAvailable(request):
    return render(request, 'application/de_notavailable.html',)

