from django.shortcuts import render

# Create your views here.

# first index page we come into
def index(request):
    return render(request, 'application/index.html',)

def page1(request):
    return render(request, 'application/page1.html',)

def page2(request):
    return render(request, 'application/page2.html',)

def page3(request):
    return render(request, 'application/page3.html',)

def page4(request):
    return render(request, 'application/page4.html',)

def page5(request):
    return render(request, 'application/page5.html',)

    
def available(request):
    return render(request, 'application/de_available.html',)

def notAvailable(request):
    return render(request, 'application/de_notavailable.html',)
