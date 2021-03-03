from django.contrib import admin
from .models import User, Addresses, Eligibility, programs
# Register your models here. This will let us see the models in the /admin portion of the sie the models we register
# TODO: Either Grace or Andrew - make sure to disable this when it is launched! we don't want anyone accessing this data

admin.site.register(User)
admin.site.register(Addresses)
admin.site.register(Eligibility)
admin.site.register(programs)