"""
URL configuration for project_tracker project.

Routes requests to appropriate views and apps.

For more details, see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    # ---------------------- ADMIN PANEL ----------------------
    path('admin/', admin.site.urls),

    # ---------------------- API ENDPOINTS ---------------------
    path('api/', include('api.urls')),                # Project, Tasks, Invites
    path('api/auth/', include('users.urls')),         # Authentication, OTP, Login

    # ---------------------- FRONTEND PAGES --------------------
    path('', TemplateView.as_view(template_name='index.html')),
    path('projects/', TemplateView.as_view(template_name='projects.html'), name='projects_html'),
    path('invite_register/', TemplateView.as_view(template_name='invite_register.html'), name='invite-register-page'),
    path('tasks/', TemplateView.as_view(template_name='tasks.html'), name='tasks'),
]

# ---------------------- STATIC FILES ---------------------------
urlpatterns += staticfiles_urlpatterns()
