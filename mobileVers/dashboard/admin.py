from django.contrib import admin

# Register your models here.
from .models import Form, Feedback
# Register your models here. This will let us see the models in the /admin portion of the sie the models we register
# TODO: Either Grace or Andrew - make sure to disable this when it is launched! we don't want anyone accessing this data

admin.site.register(Form)
admin.site.register(Feedback)
