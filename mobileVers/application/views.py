from django.shortcuts import render, redirect, reverse


from .forms import UserForm, AddressForm, EligibilityForm

# TODO: Create FBV views that take into account error messages so we can show custom pages

formPageNum = 5

# first index page we come into
def index(request):
    return render(request, 'application/index.html',)

def address(request):
    if request.method == "POST": 
        form = AddressForm(request.POST or None)
        # print(form.data)
        # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
        if form.is_valid():
            # NOTE FOR ANDREW: Check if they are neighbor to neighbor here! and redirect to DE available!
            form.n2n = True;
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
        # Check password with Confirm Password field, 
        # maybe also do some password requirements here too
        form = EligibilityForm(request.POST)
        if form.is_valid():
            # Add Error MESSAGE IF THEY DIDN"T WRITE CORRECT THINGS TO SUBMIT
            # Make sure password isn't getting saved twice
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

