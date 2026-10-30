"""
URL configuration for GoPlan.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings

def serve_static(request, path, **kwargs):
    """
    Robust static file server that works in production (DEBUG=False)
    across Render, Vercel, and local setups without relying on external web server configs.
    """
    # 1. Search in STATICFILES_DIRS (source static folder)
    for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path):
            return serve(request, path, document_root=static_dir)

    # 2. Search in STATIC_ROOT (collected static files)
    if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT and os.path.exists(settings.STATIC_ROOT):
        collected_path = os.path.join(settings.STATIC_ROOT, path)
        if os.path.exists(collected_path):
            return serve(request, path, document_root=settings.STATIC_ROOT)

    # Default fallback
    return serve(request, path, document_root=settings.STATICFILES_DIRS[0])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    re_path(r'^static/(?P<path>.*)$', serve_static),
]
