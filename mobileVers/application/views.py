from django.shortcuts import render, redirect, reverse


from .forms import UserForm, AddressForm, EligibilityForm
from .backend import addressCheck, validateUSPS

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
        # print(form.data)
        if form.is_valid():
            dict = validateUSPS(form)
            try:
                addressResult = addressCheck(dict['AddressValidateResponse']['Address']['Address2'])
            except KeyError:
                pass
            if addressResult == True:
                form.n2n = True
                return redirect(reverse("application:available"))
            print(form)
            form.save()
            return redirect(reverse("application:account"))
    else:
        form = AddressForm()
    return render(request, 'application/address.html', {
        'form':form,
        'step':1,
        'formPageNum':formPageNum,
    })

def account(request):
    if request.method == "POST": 
        # Check password with Confirm Password field, 
        # maybe also do some password requirements here too
        form = UserForm(request.POST)
        if form.is_valid():
            # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
            # Make sure password isn't getting saved twice
            form.save()
            return redirect(reverse("application:finances"))
    else:
        form = UserForm()
    return render(request, 'application/account.html', {
        'form':form,
        'step':2,
        'formPageNum':formPageNum,
    })

def finances(request):
    if request.method == "POST": 
        form = EligibilityForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("application:programs"))
    else:
        form = EligibilityForm()
    return render(request, 'application/finances.html', {
        'form':form,
        'step':3,
        'formPageNum':formPageNum,
    })

def programs(request):
    return render(request, 'application/page4.html',)

def available(request):
    return render(request, 'application/de_available.html',)

def notAvailable(request):
    return render(request, 'application/de_notavailable.html',)

