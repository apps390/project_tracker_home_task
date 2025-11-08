from django.urls import path
from .views import *

urlpatterns = [
    # ---------------------- PROJECT MANAGEMENT ----------------------
    path('projects/create/', ProjectCreateAPIView.as_view(), name='project-create'),
    path('projects/', ProjectListAPIView.as_view(), name='project-list'),
    path('projects/<slug:slug>/edit/', ProjectUpdateAPIView.as_view(), name='project-edit'),
    path('projects/<slug:slug>/delete/', ProjectDeleteAPIView.as_view(), name='project-delete'),

    # ---------------------- PROJECT INVITES -------------------------
    path('projects/<slug:slug>/invite/', ProjectInviteAPIView.as_view(), name='project-invitation'),
    path('invites/accept/<uuid:token>/', InviteRegisterAPIView.as_view(), name='invite-register'),

    # ---------------------- TASK MANAGEMENT -------------------------
    path('projects/<slug:slug>/tasks/add/', TaskCreateAPIView.as_view(), name='task-create'),
    path('tasks/<slug:slug>/edit/', TaskUpdateAPIView.as_view(), name='task-update'),
    path('tasks/<slug:slug>/delete/', TaskDeleteAPIView.as_view(), name='task-delete'),
    path('projects/<slug:slug>/task_list/', TaskListAPIView.as_view(), name='project-task-list'),

    # ---------------------- PROJECT MEMBERS -------------------------
    path('projects/<slug:slug>/members/', ProjectMembersAPIView.as_view(), name='project-members'),
    path('skills/add',ContributorSkillAPIView.as_view(),name='add_skill')
]
