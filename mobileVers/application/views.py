from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, authenticate, logout
#from django.contrib.auth.forms import UserCreationForm
#from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

from.models import User

from django.db import IntegrityError

from .forms import UserForm, AddressForm, EligibilityForm, programForm
from .backend import addressCheck, validateUSPS, broadcast_email, broadcast_sms

from dashboard.backend import what_page
formPageNum = 6

# Notes: autofill in empty rows for users who don't fill out all of their info?


# TODO: Grace - possibly make a function that automatically returns next step of the page?
# Should all of these view functions look up at this one function and figure out where they need to go next
# based on which page they are on?

# TODO: Grace - add user authorization for next pages

# first index page we come into
def index(request):
    logout(request)
    print(request.user)
    return render(request, 'application/index.html',)

def address(request):
    if request.method == "POST": 
        form = AddressForm(request.POST or None)
        print(form.data)
        if form.is_valid():
            dict = validateUSPS(form)
            try:
                addressResult = addressCheck(dict['AddressValidateResponse']['Address']['Address2'], )
            except KeyError:
                print("Wrong address info added")
            try:
                instance = form.save(commit=False)
                instance.user_id = request.user
                instance.save()
            except IntegrityError:
                print("User already has information filled out for this section")
            return redirect(reverse("application:finances"))
    else:
        form = AddressForm()
    page = what_page(request.user)

    print(page)
    if what_page(request.user) == "application:address":
        return render(request, 'application/address.html', {
            'form':form,
            'step':2,
            'request.user':request.user,
            'formPageNum':formPageNum,
        })
    else:
        return redirect(reverse(page))


def account(request):
    if request.method == "POST": 
        # maybe also do some password requirements here too
        form = UserForm(request.POST)
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

    # Check if user is already logged in and has an account; just push them to next step of application
    page = what_page(request.user)
    if what_page(request.user) == "application:account":
        return render(request, 'application/account.html', {
        'form':form,
        'step':1,
        'formPageNum':formPageNum,
    })
    else:
        return redirect(reverse(page))

def finances(request):
    if request.method == "POST": 
        form = EligibilityForm(request.POST)
        if form.is_valid():
            print(form.data)
            try:
                instance = form.save(commit=False)
                # NOTE FOR ANDREW: This was that stupid line that caused user auth to not work 
                instance.user_id = request.user
                instance.save()
                return redirect(reverse("application:programs"))
            except IntegrityError:
                print("User already has information filled out for this section")
        else:
            print(form.data)
    else:
        form = EligibilityForm()

    page = what_page(request.user)
    if what_page(request.user) == "application:finances":
        return render(request, 'application/finances.html', {
        'form':form,
        'step':3,
        'formPageNum':formPageNum,
    })
    else:
        return redirect(reverse(page))


def programs(request):
    if request.method == "POST": 
        form = programForm(request.POST)

##                current_user = request.user
 #       record_data = programs.objects.get(user_id = current_user)
 #       form = programForm(request.POST, instance = record_data)
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

    page = what_page(request.user)
    if what_page(request.user) == "application:programs":
        return render(request, 'application/programs.html', {
        'form':form,
        'step':4,
        'formPageNum':formPageNum,
    })

    else:
        return redirect(reverse(page))
    #return render(request, 'application/programs.html',)

def available(request):
    return render(request, 'application/de_available.html',)

def notAvailable(request):
    return render(request, 'application/de_notavailable.html',)


