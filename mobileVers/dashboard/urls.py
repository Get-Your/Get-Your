from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

# Need to specify my urls to be used within this project
urlpatterns = [
    path('', views.feedback, name='index'), #path('', views.index, name='index'),
    # Pages for forms
    path('files', views.files, name='files'),
    path('filesContinued', views.filesContinued, name='filesContinued'),
    path('addressVerification', views.addressVerification, name='addressVerification'),
    path('login', views.login_user, name='login'),
    path('broadcast', views.broadcast, name='broadcast'),
    path('feedbackReceived', views.feedbackReceived, name="feedbackReceived"),
    path('manualVerifyIncome', views.manualVerifyIncome, name='manualVerifyIncome'),
    path('notifyRemaining', views.notifyRemaining, name='notifyRemaining'),
    path('underConstruction', views.underConstruction, name='underConstruction'),
    path('GetFOCO', views.dashboardGetFoco, name='dashboard'),
    path('qualifiedPrograms', views.qualifiedPrograms, name='qualifiedPrograms'),
    path('ProgramsList', views.ProgramsList, name='ProgramsList'),
    path('FAQ', views.FAQ, name='FAQ'),
    path('settings', views.settings, name='settings'),
    # Available/NotAvailable Digital equity in your area
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) #this is needed to get file uploads to work! 
