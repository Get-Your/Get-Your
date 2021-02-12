from django.urls import path


from . import views

# Need to specify my urls to be used within this project
urlpatterns = [
    path('', views.index, name='index'),
    path('page1', views.page1, name='page1'),
    path('page2', views.page2, name='page2'),
    path('page3', views.page3, name='page3'),
    path('page4', views.page4, name='page4'),
    path('page5', views.page5, name='page5'),
    path('available', views.available, name='available'),
    path('notAvailable', views.notAvailable, name='notAvailable'),

]
