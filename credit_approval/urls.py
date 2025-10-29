"""
URL configuration for credit_approval project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('credit_system.urls')),
]
