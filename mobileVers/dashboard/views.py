from django.shortcuts import render, redirect, reverse

# Create your views here.

# first index page we come into
def index(request):
    if request.user.is_authenticated:
        user = request.user.addresses
        print(user)
        return render(request, "dashboard/index.html", {"user" : user})
    else:
        print("notautnehticated")
        return render(request, 'dashboard/layout.html',)

def snap(request):
    return render(request, 'dashboard/SNAP.html',)

def freeReduced(request):
    return render(request, 'application/layout.html',)

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

