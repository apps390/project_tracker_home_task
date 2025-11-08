import logging
from rest_framework import generics, status
from rest_framework.response import Response
from django.conf import settings
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import ValidationError
from project_tracker.utils.response_handler import build_response
from .serializers import *
from .decorators import manager_required
from django.shortcuts import get_object_or_404
from .models import *
from django.core.mail import send_mail,EmailMultiAlternatives
from .utils.project_validators import validate_project_access,validate_project_member_access
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from django.template.loader import render_to_string




logger = logging.getLogger('tracker_logger')


class ProjectCreateAPIView(generics.CreateAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @manager_required
    def post(self, request, *args, **kwargs):
        logger.debug("Entered ProjectCreateAPIView.post()")

        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            project = serializer.save(created_by=request.user)
            logger.info(f"Project '{project.name}' created successfully by {request.user.email}")

            return build_response(True,message="Project created successfully.",data=serializer.data,status_code=status.HTTP_201_CREATED,)

        except ValidationError as e:
            logger.warning(f"Validation error during project creation by {request.user.email}: {e.detail}")
            return build_response(False,message="Validation error occurred.",errors=e.detail,status_code=status.HTTP_400_BAD_REQUEST,)

        except Exception as e:
            logger.exception(f"Unexpected error during project creation by {request.user.email}: {e}")
            return build_response(False,errors="An unexpected error occurred while creating the project.",status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,)
class ProjectUpdateAPIView(generics.UpdateAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    queryset = Project.objects.all()
    @manager_required
    def get(self, request, slug, *args, **kwargs):
        """Get project details for editing"""
        logger.debug(f"Project details request by {request.user.email} for slug: {slug}")
        
        try:
            project = self.get_object()
            
            invalid_response = validate_project_access(project, request.user, "View Project")
            if invalid_response:
                return invalid_response
                
            serializer = self.get_serializer(project)
            logger.info(f"Project '{project.name}' details retrieved by {request.user.email}")
            return build_response(
                True, 
                message="Project details retrieved successfully.", 
                data=serializer.data, 
                status_code=status.HTTP_200_OK
            )
            
        except Exception as exc:
            logger.exception(f"Unexpected error during project details retrieval by {request.user.email}: {exc}")
            return build_response(
                False, 
                errors="An unexpected error occurred while retrieving project details.", 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @manager_required
    def patch(self, request, slug, *args, **kwargs):
        logger.debug(f"Project update attempt by {request.user.email} for slug: {slug}")

        try:
            project = get_object_or_404(Project, slug=slug)

            invalid_response = validate_project_access(project, request.user, "Update Project")
            if invalid_response:
                return invalid_response
            serializer = self.get_serializer(project, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            logger.info(f"Project '{project.name}' updated successfully by {request.user.email}")
            return build_response(True, message="Project updated successfully.", data=serializer.data, status_code=status.HTTP_200_OK)

        except ValidationError as exc:
            logger.warning(f"Validation error during update by {request.user.email}: {exc.detail}")
            return build_response(
                False,
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as exc:
            logger.exception(f"Unexpected error during project update by {request.user.email}: {exc}")
            return build_response(False, errors="An unexpected error occurred while updating the project.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
class ProjectDeleteAPIView(generics.DestroyAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    queryset = Project.objects.all()

    @manager_required
    def delete(self, request, slug, *args, **kwargs):
        logger.debug(f"Delete request for project slug: {slug} by {request.user.email}")

        try:
            project = get_object_or_404(Project, slug=slug)

            invalid_response = validate_project_access(project, request.user, "Delete project")
            if invalid_response:
                return invalid_response

            project.is_deleted = True
            project.save()

            logger.info(f"Project '{project.name}' soft deleted by {request.user.email}")
            return build_response(True, message="Project deleted successfully.", status_code=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception(f"Error during project deletion: {exc}")
            return build_response(False, errors="An unexpected error occurred while deleting the project.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
class ProjectPagination(PageNumberPagination):
    """Custom pagination class for Projects."""
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50


class ProjectListAPIView(generics.ListAPIView):
    serializer_class = ProjectSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ProjectPagination

    def get_queryset(self):
        """Filter projects based on the logged-in user's relation and status."""
        user = self.request.user
        status_filter = self.request.query_params.get('status')

        try:
            queryset = Project.objects.filter(is_deleted=False).filter(
                models.Q(created_by=user) | models.Q(members__user=user)
            ).distinct()

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            return queryset.order_by('-created_at')

        except Exception as e:
            logger.exception(f"Error fetching queryset for user {user.email}: {e}")
            return Project.objects.none()

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"project_list:{user.id}:{request.get_full_path()}"

        try:
            # Try fetching from cache
            try:
                cached_data = cache.get(cache_key)
            except Exception as cache_error:
                logger.warning(f"Cache get failed for key {cache_key}: {cache_error}")
                cached_data = None

            if cached_data:
                logger.debug(f"Serving project list for {user.email} from cache")
                return Response(cached_data)

            # Fetch from DB (normal flow)
            logger.debug(f"Fetching project list for user: {user.email}")
            response = super().list(request, *args, **kwargs)

            # Try setting cache but ignore cache errors
            try:
                cache.set(cache_key, response.data, timeout=60 * 5)
            except Exception as cache_error:
                logger.warning(f"Cache set failed for key {cache_key}: {cache_error}")

            return response

        except Exception as e:
            logger.exception(f"Unexpected error listing projects for {user.email}: {e}")
            return build_response(
                False,
                "Failed to retrieve projects. Please try again later.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        
class ProjectInviteAPIView(generics.GenericAPIView):
    serializer_class = ProjectInviteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @manager_required
    def post(self, request, slug):
        logger.debug(f"Invite request received for project slug: {slug}")
        project = get_object_or_404(Project, slug=slug)

        invalid_response = validate_project_access(project, request.user, "invite members")
        if invalid_response:
            return invalid_response

        try:
            emails = request.data.get('email') or request.data.get('emails', [])
            
            if isinstance(emails, str):
                emails = [emails]
            
            if not emails:
                return build_response(False,errors="No email provided for invitation.",status_code=status.HTTP_400_BAD_REQUEST)

            successful_invites = []
            
            for email in emails:
                serializer_data = {'email': email}
                serializer = self.get_serializer(data=serializer_data, context={'project': project})
                serializer.is_valid(raise_exception=True)

                validated_email = serializer.validated_data['email']
                user = User.objects.filter(email=validated_email).first()

                if user and hasattr(user, 'contributor_profile'):
                    contributor = user.contributor_profile
                    project.members.add(contributor)
                    logger.info(f"Existing contributor {validated_email} added directly to project {project.name}")
                    successful_invites.append(validated_email)
                    continue

                invite = ProjectInvite.objects.create(
                    project=project,
                    invited_by=request.user,
                    email=validated_email
                )

                invite_link = f"{settings.BASE_URL}/invite_register?token={invite.token}"
                logger.info(f"Invite created for {validated_email} with link {invite_link}")

                self.send_html_invitation_email(project, invite, request.user, invite_link)

                successful_invites.append(validated_email)

            if len(successful_invites) == 1:
                return build_response(True, f"Invitation sent successfully to {successful_invites[0]}.", status.HTTP_201_CREATED)
            else:
                return build_response(True, f"Invitations sent successfully to {len(successful_invites)} emails.", status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception(f"Error in project invitation: {e}")
            return build_response(False, errors=str(e),status_code= status.HTTP_400_BAD_REQUEST)

    def send_html_invitation_email(self, project, invite, inviter, invite_link):
        """Send HTML invitation email using template from frontend directory"""
        try:
            # Context data for the template - matches your template variables
            context = {
                'project_name': project.name,
                'inviter_name': f"{inviter.first_name} {inviter.last_name}",
                'inviter_email': inviter.email,
                'invite_link': invite_link,
                'recipient_email': invite.email,
            }
            
            html_content = render_to_string('project_invitation.html', context)
            
            text_content = f"""
            You've been invited to join '{project.name}'
            
            Invited by: {inviter.first_name} {inviter.last_name} ({inviter.email})
            
            Accept your invitation: {invite_link}
            
            This link will expire in 48 hours.
            
            If you have any questions, please contact {inviter.email}
            """
            
            email = EmailMultiAlternatives(
                subject=f"🎯 Join {project.name} on Project Tracker",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invite.email],
            )
            
            email.attach_alternative(html_content, "text/html")
            
            email.send(fail_silently=True)
            logger.info(f"HTML invitation email sent successfully to {invite.email}")
            
        except Exception as e:
            logger.error(f"Failed to send HTML email to {invite.email}: {e}")
            send_mail(
                subject=f"Invitation to join project: {project.name}",
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invite.email],
                fail_silently=True,
            )
            logger.info(f"Fallback text email sent to {invite.email}")
        
class InviteRegisterAPIView(generics.GenericAPIView):
    serializer_class = InviteRegisterSerializer
    permission_classes = [AllowAny]


    def post(self, request, token):
        logger.debug(f"Invite registration attempt for token: {token}")

        try:
            serializer = self.get_serializer(data={**request.data, "token": token})
            serializer.is_valid(raise_exception=True)
            data = serializer.save()

            logger.info(f"User {data['email']} successfully registered and joined project {data['project']}")
            return build_response(True,"Account created and invitation accepted successfully.",data=data,status_code=status.HTTP_201_CREATED)
        except ValidationError as exc:
            logger.warning(f"Validation error at register invitation api")
            return build_response(
                False,
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Error during invite registration: {e}")
            return build_response(False, errors=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        

class TaskCreateAPIView(generics.CreateAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, *args, **kwargs):
        logger.debug(f"Task creation attempt under project: {slug}")

        try:
            project = get_object_or_404(Project, slug=slug, is_deleted=False)
            invalid_response = validate_project_member_access(project, request.user, "Create Task")
            if invalid_response:
                return invalid_response
            serializer = self.get_serializer(data=request.data, context={'project': project})
            serializer.is_valid(raise_exception=True)

            task = serializer.save(project=project)
            assigned_to = serializer.validated_data.get('assigned_to', [])
            if assigned_to:
                task.assigned_to.set(assigned_to)

            logger.info(f"Task '{task.title}' created successfully under project '{project.name}'")

            return build_response(True,"Task created successfully.",data=serializer.data,status_code=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            logger.warning(f"Validation error during task creation: {e.detail}")
            return build_response(False, errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Unexpected error while creating task: {e}")
            return build_response(False, "Failed to create task.", status_code=status.HTTP_400_BAD_REQUEST)
        
class TaskUpdateAPIView(generics.UpdateAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"


    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=user) | models.Q(members__user=user)
            ),
            is_deleted=False
        )

    def get(self, request, slug, *args, **kwargs):
        logger.debug(f"Task retrieval attempt for task slug: {slug} by {request.user.email}")

        try:
            task = self.get_object()
            serializer = self.get_serializer(task)
            
            logger.info(f"Task '{task.title}' retrieved successfully by {request.user.email}")
            return build_response(
                True,
                "Task retrieved successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Task.DoesNotExist:
            logger.warning(f"Task with slug {slug} not found for user {request.user.email}")
            return build_response(False, errors="Task not found.", status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Unexpected error during task retrieval for {slug}: {e}")
            return build_response(False, errors="Failed to retrieve task.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, slug, *args, **kwargs):
        logger.debug(f"Task update attempt for task slug: {slug} by {request.user.email}")

        try:
            task = get_object_or_404(Task, slug=slug)
            project = task.project

            invalid_response = validate_project_member_access(project, request.user, "update this task")
            if invalid_response:
                return invalid_response

            serializer = self.get_serializer(task, data=request.data, partial=True, context={'project': project})
            serializer.is_valid(raise_exception=True)
            updated_task = serializer.save()

            if 'assigned_to' in serializer.validated_data:
                updated_task.assigned_to.set(serializer.validated_data['assigned_to'])
                updated_task.save()

            logger.info(f"Task '{updated_task.title}' updated successfully by {request.user.email}")
            return build_response(
                True,
                "Task updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            logger.warning(f"Validation error during task updation: {e.detail}")
            return build_response(False, errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Unexpected error during task update for {slug}: {e}")
            return build_response(False, errors="Failed to update task.", status_code=status.HTTP_400_BAD_REQUEST)
class TaskDeleteAPIView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    queryset = Task.objects.all()

    def delete(self, request, slug, *args, **kwargs):
        logger.debug(f"Task delete request received for {slug} by {request.user.email}")

        try:
            task = get_object_or_404(Task, slug=slug)
            project = task.project

            invalid_response = validate_project_member_access(project, request.user, "delete this task")
            if invalid_response:
                return invalid_response

            if task.is_deleted:
                return build_response(False, errors="Task is already deleted.", status_code=status.HTTP_400_BAD_REQUEST)

            task.is_deleted = True
            task.save(update_fields=["is_deleted"])

            logger.info(f"Task '{task.title}' soft-deleted by {request.user.email}")
            return build_response(True, "Task deleted successfully.", status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Unexpected error during task deletion: {e}")
            return build_response(False, errors="Failed to delete task.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskListAPIView(generics.ListAPIView):
    serializer_class = TaskListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ProjectPagination  

    def get_queryset(self):
        user = self.request.user
        project_slug = self.kwargs.get('slug')
        status_filter = self.request.query_params.get('status')
        try:
            project = (
                Project.objects
                .select_related('created_by')  # ✅ Eager load creator
                .prefetch_related('members__user')  # ✅ Preload all member-user pairs
                .filter(slug=project_slug, is_deleted=False)
                .filter(models.Q(created_by=user) | models.Q(members__user=user))
                .distinct()
                .first()
            )

            if not project:
                logger.warning(f"User {user.email} attempted to access tasks for project {project_slug} without permission")
                return Task.objects.none()

            queryset = (
                Task.objects
                .select_related('project')  
                .prefetch_related('assigned_to__user')  
                .filter(project=project, is_deleted=False)
            )

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            return queryset.order_by('-created_at')

        except Exception as e:
            logger.error(f"Error fetching tasks for project {project_slug}: {e}")
            return Task.objects.none()

    def list(self, request, *args, **kwargs):
        user = request.user
        project_slug = self.kwargs.get('slug')
        cache_key = f"task_list:{user.id}:{project_slug}:{request.get_full_path()}"

        try:
            try:
                cached_data = cache.get(cache_key)
            except Exception as cache_error:
                logger.warning(f"Cache get failed for key {cache_key}: {cache_error}")
                cached_data = None

            if cached_data:
                logger.debug(f"Serving task list for project {project_slug} and user {user.email} from cache")
                return Response(cached_data)

            # Fetch from DB (normal flow)
            logger.debug(f"Fetching task list for project: {project_slug} and user: {user.email}")
            response = super().list(request, *args, **kwargs)

            # Try setting cache but ignore cache errors
            try:
                cache.set(cache_key, response.data, timeout=60 * 5)
            except Exception as cache_error:
                logger.warning(f"Cache set failed for key {cache_key}: {cache_error}")

            return response

        except Exception as e:
            logger.exception(f"Unexpected error listing tasks for project {project_slug} and user {user.email}: {e}")
            return build_response(
                False,
                "Failed to retrieve tasks. Please try again later.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
class ProjectMembersAPIView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        """Get all members of a project (excluding project creator)"""
        try:
            user = request.user
            project = Project.objects.filter(
                slug=slug,
                is_deleted=False
            ).filter(
                models.Q(created_by=user) | models.Q(members__user=user)
            ).distinct().first()

            if not project:
                return build_response(False, "Project not found", status_code=status.HTTP_404_NOT_FOUND)

            members = []
            
            for contributor in project.members.all():
                member_data = {
                    'id': contributor.id,
                    'email': contributor.user.email,
                    'name': f"{contributor.user.first_name} {contributor.user.last_name}".strip(),
                    'role': getattr(contributor, 'role', 'member')
                }
                members.append(member_data)

            return build_response(
                True,
                "Project members retrieved successfully",
                data=members,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f"Error fetching project members for {slug}: {e}")
            return build_response(False, "Failed to retrieve project members", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContributorSkillAPIView(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SkillSerializer

    def get(self, request):
        try:
            contributor = get_object_or_404(Contributor, user=request.user)
            serializer = self.get_serializer(contributor)
            return build_response(
                success=True,
                message="Fetched contributor skills successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching skills: {str(e)}")
            return build_response(success=False, errors=str(e))

    def post(self, request):
        try:
            contributor = get_object_or_404(Contributor, user=request.user)
            serializer = self.get_serializer(contributor, data=request.data, partial=True)

            serializer.is_valid(raise_exception=True)
            serializer.save()

            return build_response(
                success=True,
                message="Skills updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        except ValidationError as e:
            logger.warning(f"Validation error in ContributorSkillAPIView: {e}")
            return build_response(success=False, errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error in ContributorSkillAPIView: {str(e)}")
            return build_response(success=False, errors=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
