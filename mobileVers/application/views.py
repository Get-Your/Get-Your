from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm

from django.db import IntegrityError

from .forms import UserForm, AddressForm, EligibilityForm, programForm
from .backend import addressCheck, validateUSPS, email

formPageNum = 5

# TODO: Grace - possibly make a function that automatically returns next step of the page?
# Should all of these view functions look up at this one function and figure out where they need to go next
# based on which page they are on?

# TODO: Grace - add user authorization for next pages

# first index page we come into
def index(request):
    return render(request, 'application/index.html',)

def address(request):
    if request.method == "POST": 
        form = AddressForm(request.POST or None)
        print(form.data)
        if form.is_valid():
            dict = validateUSPS(form)
            try:
                addressResult = addressCheck(dict['AddressValidateResponse']['Address']['Address2'])
            except KeyError:
                print("Wrong address info added")
            if addressResult == True:
                form.n2n = True
                return redirect(reverse("application:available"))
            print(form)
            form.save()
            return redirect(reverse("application:finances"))
    else:
        form = AddressForm()
    return render(request, 'application/address.html', {
        'form':form,
        'step':2,
        'formPageNum':formPageNum,
    })

def account(request):
    if request.method == "POST": 
        # maybe also do some password requirements here too
        form = UserForm(request.POST)
        if form.is_valid():
            # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
            # Make sure password isn't getting saved twice
            #email(form['email'].value(),)
            print(form.data)
            try:                
                form.save()
                email = form.cleaned_data.get("email")
                # Check that password matches the confirmation
                password = form.cleaned_data.get("password")
                user = authenticate(email=email, password=password)
                login(request,user)
                print("userloggedin")
            # TODO: GRACE - check if this error actually works
            except IntegrityError:
                return render(request, "application/account.html", {
                    "message": "Username already taken."
                })
            return redirect(reverse("dashboard:index"))
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
            return redirect(reverse("dashboard:snap"))
            
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

