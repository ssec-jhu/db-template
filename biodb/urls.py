"""biodb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from decorator_include import decorator_include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.views.static import serve

from uploader import views
from uploader.admin import data_admin
from catalog.admin import catalog_admin


admin.site.site_header = settings.SITE_HEADER

urlpatterns = [
    path(r"healthz/", include("health_check.urls")),
    path("version/", views.version, name="version"),
    path("favicon.ico", views.favicon),
    path('', RedirectView.as_view(pattern_name="home", permanent=True)),
    path('uploader/', include('biodb.apps.uploader.urls')),
    path('home/', views.home, name='home'),

    # Note: The following perms are also specified by settings.EXPLORER_PERMISSION_VIEW and
    # settings.EXPLORER_PERMISSION_CHANGE.
    path('explorer/', decorator_include(user_passes_test(lambda x: (x.is_active and x.is_staff) and
                                                         (x.is_superuser or
                                                          getattr(x, "is_sqluser_view", False) or
                                                          getattr(x, "is_sqluser_change", False)),
                                                         login_url="/admin/login/"),
                                        'explorer.urls')),
    path('data/', data_admin.urls),
    path('catalog/', catalog_admin.urls),

    path("admin/password_reset/",
         auth_views.PasswordResetView.as_view(from_email=settings.EMAIL_FROM,
                                              extra_context={"site_header": admin.site.site_header}),
         name="admin_password_reset"),
    path("admin/password_reset/done/",
         auth_views.PasswordResetDoneView.as_view(extra_context={"site_header": admin.site.site_header}),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(extra_context={"site_header": admin.site.site_header}),
         name="password_reset_confirm"),
    path("reset/done/",
         auth_views.PasswordResetCompleteView.as_view(extra_context={"site_header": admin.site.site_header}),
         name="password_reset_complete"),
    path('admin/', admin.site.urls)
]


@login_required(login_url="/admin/login/")
def protected_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)


urlpatterns += static(settings.MEDIA_URL, view=protected_serve, document_root=settings.MEDIA_ROOT)
