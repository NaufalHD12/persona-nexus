"""
URL configuration for personanexus project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Hapus SignupView, kita akan gunakan view baru
from app.views import LandingPageView # <-- Impor view baru

urlpatterns = [
    path('admin/', admin.site.urls),
    # === UBAH URL ROOT DI SINI ===
    path('', LandingPageView.as_view(), name="landing_page"), 
    path('accounts/', include('allauth.urls')),
    path('feed/', include("app.urls")),
    path('tinymce/', include('tinymce.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
    path('management/', include('app.management_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
