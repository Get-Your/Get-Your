from django.shortcuts import render, redirect, reverse
from .forms import FileForm, FeedbackForm, TaxForm, addressVerificationForm, AddressForm

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
                checkAllForms = [not(request.user.programs.snap),not(request.user.programs.freeReducedLunch),] #TODO 4/24 include not(request.user.programs.1040) here not(request.user.programs.Identification),
                for group in Forms.all():
                    if group.document_title == "SNAP":
                        checkAllForms[0] = True
                        file_list["SNAP Card"] = False
                    if group.document_title == "Free and Reduced Lunch":
                        checkAllForms[1] = True
                        file_list["PSD Reduced Lunch Approval Letter"] = False
                    
                    #TODO 4/24 UPDATE TAX BELOW
                    if group.document_title == "1040 Form":
                        checkAllForms[4] = True
                        file_list["1040 Tax Form"] = False
                    '''
                    if group.document_title == "Identification":
                        checkAllForms[3] = True
                        file_list["Identification"] = False
                    '''

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



def addressVerification(request):
    if request.method == "POST":
        try:
            existing = request.user.addressverification
            form = addressVerificationForm(request.POST,instance = existing)
        except AttributeError or ObjectDoesNotExist:
            form = addressVerificationForm(request.POST or None)
        if form.is_valid():
            print(form.data)
            print(request.session)
            try:
                instance = form.save(commit=False)
                instance.user_id = request.user
                instance.save()
                return redirect(reverse("dashboard:filesContinued"))
            except IntegrityError:
                print("User already has information filled out for this section")
            return redirect(reverse("application:available"))
    else:
        form = addressVerificationForm()

    return render(request, 'dashboard/addressVerification.html', {
    'form':form,
    'step':1,
    'formPageNum':2,
    })

#    else:
#        return redirect(reverse(page))
    #return render(request, 'application/programs.html',)






def filesContinued(request):
    file_list = {   "Identification": request.user.addressverification.Identification,
                    "Utility Bill": request.user.addressverification.Utility,
                    "PSD Reduced Lunch Approval Letter": request.user.addressverification.freeReducedLunch,
    }

    if request.method == "POST":   
        form = AddressForm(request.POST, request.FILES)
        if form.is_valid():
            print(form)  
            if request.user.is_authenticated:
                instance = form.save(commit=False)
                print(instance)
                instance.user_id = request.user
                instance.save()
                
                file_upload = request.user
                file_upload.address_files.add(instance)

                # Check if the user needs to upload another form
                Forms = request.user.address_files
                checkAllForms = [not(request.user.addressverification.Identification),not(request.user.addressverification.Utility),not(request.user.addressverification.freeReducedLunch),]
                for group in Forms.all():
                    if group.document_title == "Identification":
                        checkAllForms[0] = True
                        file_list["Identification"] = False
                    if group.document_title == "Utility":
                        checkAllForms[1] = True
                        file_list["Utility Bill"] = False
                    if group.document_title == "Free and Reduced Lunch": 
                        checkAllForms[2] = True
                        file_list["PSD Reduced Lunch Approval Letter"] = False

                if False in checkAllForms:
                    return render(request, 'dashboard/filesContinued.html', {
                            'form':form,
                            'programs': file_list,
                            'program_string': files_to_string(file_list),
                            'step':2,
                            'formPageNum':2,
                        })
                return redirect(reverse("application:RecreationQuickApply")) 
            else:
                print("notautnehticated")
                # TODO: Change this link
                return render(request, 'dashboard/layout.html',)
    else:
        form = AddressForm()
    print(file_list)
    return render(request, 'dashboard/filesContinued.html', {
    'form':form,
    'programs': file_list,
    'program_string': files_to_string(file_list),
    'step':2,
    'formPageNum':2,
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
    #active_program_count = Program.objects..wherecurrent_user.
    return render(request, 'dashboard/index.html', #{
   #     "active_program_count": active_program_count}
    )
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


def qualifiedPrograms(request):
    if request.user.eligibility.DEqualified == True:
        text = "True"
    else:
        text = "False"
    if request.user.programs.snap == True or request.user.programs.freeReducedLunch == True:
        text2 = "True"
    else:
        text2 = "False"
    return render(request, 'dashboard/qualifiedPrograms.html',{
        "page_title": "Qualified Programs",
        "dashboard_color": "white",
        "program_list_color": "var(--yellow)",
        "FAQ_color": "white",
        "Settings_color": "white",
        "Privacy_Policy_color": "white",
        
        "GRPreQualification": text,
        "RecreationPreQualification": text2,})

 
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
        text4 = "Click here to quick apply for Grocery Rebate Tax Program"
        text5 = ""
        text6 = "Click here to quick apply for Recreation"
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

# Everything under here is for new dashboard
def dashboardGetFoco(request):
    return render(request, 'dashboard/dashboard_GetFoco.html',{
        "page_title": "Get: FOCO",
        "dashboard_color": "var(--yellow)",
        "program_list_color": "white",
        "FAQ_color": "white",
        "Settings_color": "white",
        "Privacy_Policy_color": "white",})

def ProgramsList(request):
    return render(request, 'dashboard/qualifiedPrograms.html',{
        "page_title": "Programs List",
        "dashboard_color": "white",
        "program_list_color": "var(--yellow)",
        "FAQ_color": "white",
        "Settings_color": "white",
        "Privacy_Policy_color": "white",})


def FAQ(request):
    return render(request, 'dashboard/FAQ.html',{
        "page_title": "FAQ",
        "dashboard_color": "white",
        "program_list_color": "white",
        "FAQ_color": "var(--yellow)",
        "Settings_color": "white",
        "Privacy_Policy_color": "white",})
