from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

# Need to specify my urls to be used within this project
urlpatterns = [
    path('', views.feedback, name='index'), #path('', views.index, name='index'),
    # Pages for forms
    path('files', views.files, name='files'),
    path('login', views.login_user, name='login'),
    path('broadcast', views.broadcast, name='broadcast'),
    path('feedbackReceived', views.feedbackReceived, name="feedbackReceived"),
    path('manualVerifyIncome', views.manualVerifyIncome, name='manualVerifyIncome'),
    # Available/NotAvailable Digital equity in your area
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) #this is needed to get file uploads to work! 
