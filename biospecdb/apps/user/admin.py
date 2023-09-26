from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from user.models import Center, User

admin.site.register(User, BaseUserAdmin)
admin.site.register(Center)
