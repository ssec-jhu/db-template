from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from user.models import Center, User


@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    fields = ("name", "country", "id")
    list_display = ("name", "country", "patient_count")
    readonly_fields = ("id",)

    def patient_count(self, obj):
        from uploader.models import Patient
        return Patient.objects.filter(center=obj.pk).count()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form_template = "admin/auth/user/add_form.html"
    change_user_password_template = None
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "center")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_catalogviewer",
                    "is_sqluser_view",
                    "is_sqluser_change",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "center"),
            },
        ),
    )
    list_display = ("username", "email", "center", "first_name", "last_name", "is_staff")
    list_filter = ("center", "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "center", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )
