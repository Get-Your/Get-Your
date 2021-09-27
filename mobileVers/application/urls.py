from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

# Need to specify my urls to be used within this project
urlpatterns = [
    path('', views.index, name='index'),
    # Pages for forms
    path('address', views.address, name='address'),
    path('account', views.account, name='account'),
    path('finances', views.finances, name='finances'),
    path('programs', views.programs, name='programs'),
    path('attestation', views.attestation, name='attestation'),
    path('moreInfoNeeded', views.moreInfoNeeded, name='moreInfoNeeded'),
    

    # Available/NotAvailable Digital Equity in your area
    # path('available', views.available, name='available'),
    path('notAvailable', views.notAvailable, name='notAvailable'),
    path('quickAvailable', views.quickAvailable, name='quickAvailable'),
    path('quickNotAvailable', views.quickNotAvailable, name='quickNotAvailable'),
    path('quickComingSoon', views.quickComingSoon, name='quickComingSoon'),
    path('quickNotFound', views.quickNotFound, name='quickNotFound'),
    path('addressCorrection', views.addressCorrection, name='addressCorrection'),
    path('inServiceArea', views.inServiceArea, name='inServiceArea'),
    path('GRQuickApply', views.GRQuickApply, name='GRQuickApply'),
    path('takeUSPSaddress', views.takeUSPSaddress, name='takeUSPSaddress'),
    # Grocery Rebate Dependent Pages
    path('callUs', views.callUs, name='callUs'),
    # Recreation Dependent Pages
    path('RecreationQuickApply', views.RecreationQuickApply, name='RecreationQuickApply'),
    path('ConnexionQuickApply', views.ConnexionQuickApply, name='ConnexionQuickApply'),
    path('comingSoon', views.comingSoon, name='comingSoon'),
    # ETC. pages
    path('mayQualify', views.mayQualify, name='mayQualify'),
    path('privacyPolicy', views.privacyPolicy, name='privacyPolicy'),
    path('dependentInfo', views.dependentInfo, name='dependentInfo'),
    
    path('ajax/load-gahi/', views.load_gahi_selector, name='ajax_load_gahi'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) #this is needed to get file uploads to work! 
