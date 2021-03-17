from django.shortcuts import render, redirect, reverse
from .forms import FileForm, FeedbackForm

from .models import User, Form

from .backend import authenticate, files_to_string, what_page
from django.contrib.auth import get_user_model, login, authenticate, logout
from application.backend import broadcast_email, broadcast_sms
# Create your views here.

# first index page we come into


def files(request):
    page = what_page(request.user)
    print(page)
    if what_page(request.user) == "dashboard:files":

        
        # TODO: Grace Add something that checks if user logged in
        file_list = {"SNAP Card": request.user.programs.snap,
                    # Have Reduced Lunch be last item in the list if we add more programs
                    "PSD Reduced Lunch Approval Letter": request.user.programs.freeReducedLunch
        }

        if request.method == "POST":   
            form = FileForm(request.POST, request.FILES)
            print(form)
            if form.is_valid():  
                if request.user.is_authenticated:
                    instance = form.save(commit=False)
                    # NOTE FOR ANDREW: This was that stupid line that caused user auth to not work 
                    instance.user_id = request.user
                    instance.save()
                    print("File Saved")

                    # Check if the user needs to upload another form
                    Forms = Form.objects.filter(user_id = request.user)
                    checkAllForms = [not(request.user.programs.snap),not(request.user.programs.freeReducedLunch)]
                    for group in Forms.all():
                        if group.document_title == "SNAP":
                            file_list["SNAP Card"] = False
                            checkAllForms[0] = True
                        if group.document_title == "Free and Reduced Lunch":
                            checkAllForms[1] = True
                            file_list["PSD Reduced Lunch Approval Letter"] = False
                    
                    if False in checkAllForms:
                        return render(request, 'dashboard/files.html', {
                                'form':form,
                                'programs': file_list,
                                'program_string': files_to_string(file_list),
                                'step':5,
                                'formPageNum':6,
                            })
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

    else:
        return redirect(reverse(page))

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

def login_user(request):
    if request.method == "POST":
        # Try to log in user
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(username=email, password=password)
        # Check if the authentication was successful
        if user is not None:
            login(request, user)
            #TODO logic needed here to check if client has completed application or not!
            return redirect(reverse("dashboard:index"))
        else:
            return render(request, "dashboard/login.html", {
                "message": "Invalid username and/or password"
            })
    
    # If it turns out user is already logged in but is trying to log in again redirect to user's homepage
    if request.method == "GET" and request.user.is_authenticated:
        return redirect(reverse("dashboard:files"))

    # Just give back log in page if none of the above is true
    else:
        return render(request, "dashboard/login.html",{})

def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            print(form.cleaned_data['starRating'])
            print(form.cleaned_data['feedbackComments'])
            
            return redirect(reverse("application:available"))
        else:

            print("form is not valid")
            
    else:
        form = FeedbackForm()
        print("you never even got to POST")
    return render(request, 'dashboard/index.html',)















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

