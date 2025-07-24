"""
URL configuration for personanexus project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from allauth.account.views import SignupView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', SignupView.as_view(), name="landing_signup"),
    path('accounts/', include('allauth.urls')),
    path('feed/', include("app.urls")),
    path('tinymce/', include('tinymce.urls')),
    path('__reload__/', include('django_browser_reload.urls')),

    # === TAMBAHKAN URL UNTUK ADMIN KUSTOM DI SINI ===
    path('management/', include('app.management_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
