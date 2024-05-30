from django.contrib import admin
from django.conf import settings

from catalog.models import Dataset


class AuthMixin:
    """ Restrict admin access to User.is_catalogviewer. """
    def has_view_permission(self, request, obj=None):
        user = request.user
        return getattr(user, "is_catalogviewer", False) or user.is_superuser

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Note: Mutations are not allowed even by superusers.
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Dataset)
class DatasetAdmin(AuthMixin, admin.ModelAdmin):
    search_fields = ["created_at", "name", "version", "query__name"]
    list_display = ["name", "version", "file", "created_at", "size", "n_rows", "n_array_data_files"]
    date_hierarchy = "created_at"
    ordering = ("-updated_at",)
    list_filter = ("name",)
    readonly_fields = ["file",
                       "sql",
                       "app_version",
                       "sha256",
                       "size",
                       "created_at",
                       "updated_at",
                       "id",
                       "n_rows",
                       "n_array_data_files",
                       "array_data_filenames",
                       "data_sha256"]

    fieldsets = [
        (
            None,
            {
                "fields": ["query", "name", "version", "description"]
            }
        ),
        (
            "Data Product",
            {
                "fields": ["file", "sha256", "size"],
            }
        ),
        (
            "SQL",
            {
                "classes": ["collapse"],
                "fields": ["sql"],
            }
        ),
        (
            "More Details",
            {
                "classes": ["collapse"],
                "fields": [("created_at", "updated_at"),
                           "data_sha256",
                           "app_version",
                           "id",
                           "n_rows",
                           "n_array_data_files"],
            }
        ),
        (
            "Array Data Filenames",
            {
                "classes": ["collapse"],
                "fields": ["array_data_filenames"],
            }
        ),
    ]

    @admin.display
    def size(self, obj):
        if obj.file:
            return f"{int(obj.file.size / 1e6)} MB"

    @admin.display
    def n_array_data_files(self, obj):
        if obj.array_data_filenames:
            return len(obj.array_data_filenames)
        return 0


class CatalogAdminSite(admin.AdminSite):
    site_header = settings.SITE_HEADER
    index_title = "Data Catalog"
    site_title = index_title


catalog_admin = CatalogAdminSite(name="catalog_admin")
catalog_admin.register(Dataset, admin_class=DatasetAdmin)
