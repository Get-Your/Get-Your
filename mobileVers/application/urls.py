from django.urls import path


from . import views

# Need to specify my urls to be used within this project
urlpatterns = [
    path('', views.index, name='index'),
    # Pages for forms
    path('address', views.address, name='address'),
    path('account', views.account, name='account'),
    path('finances', views.finances, name='finances'),
    path('programs', views.programs, name='programs'),

    # Available/NotAvailable Digital equity in your area
    path('available', views.available, name='available'),
    path('notAvailable', views.notAvailable, name='notAvailable'),

]
