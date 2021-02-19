from django.contrib import admin
from .models import User, Addresses, Eligibility
# Register your models here.

admin.site.register(User)
admin.site.register(Addresses)
admin.site.register(Eligibility)