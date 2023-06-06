from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    #path('home/', views.home, name='Home'),
    #path('', views.upload_file, name='MetadataFileUpload'),
    #path('', views.upload_file, name='SpectradataFileUpload'),
    #path('', views.display_xlsx, name='MetadataDisplay'),
    #path("", views.index, name="index"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)