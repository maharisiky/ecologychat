from django.contrib import admin

from .models import User, Messages

admin.site.register(User)
admin.site.register(Messages)