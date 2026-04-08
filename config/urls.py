"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.http import HttpResponse
from django.conf import settings
import os

def admin_frontend_view(request, path=""):
    frontend_dir = os.path.join(settings.BASE_DIR, 'admin_frontend')
    if not path:
        path = 'index.html'
    
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
            
        content_type = "text/html"
        if path.endswith('.css'):
            content_type = "text/css"
        elif path.endswith('.js'):
            content_type = "application/javascript"
            
        return HttpResponse(content, content_type=content_type)
    return HttpResponse("Not Found", status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('', include('users.urls')),
    path('catalog/', include('exercises.urls')),
    path('me/', include('routines.urls')),
    path('me/', include('diet.urls')),
    path('me/workouts/', include('workouts.urls')),
    re_path(r'^admin-panel/(?P<path>.*)$', admin_frontend_view),
    path('admin-panel/', admin_frontend_view),
]
