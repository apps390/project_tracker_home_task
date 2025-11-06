from rest_framework import serializers
from datetime import date,datetime
import logging
from .models import *
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken


logger = logging.getLogger('tracker_logger')
User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['slug', 'created_by', 'created_at', 'updated_at']

        def validate_name(self, value):
            if not value.strip():
                raise serializers.ValidationError("Project name cannot be empty or only spaces.")
            
            instance = getattr(self, 'instance', None)
            
            qs = Project.objects.filter(name__iexact=value)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            
            if qs.exists():
                raise serializers.ValidationError("A project with this name already exists.")
            return value

    def validate_location(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Location cannot be empty or only spaces.")
        return value

    def validate_description(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Description cannot be empty or only spaces.")
        return value

    def validate(self, data):
            """
            Validate start_date and end_date to ensure proper date order.
            Also supports partial updates (PATCH).
            """
            instance = getattr(self, 'instance', None)

            start_date = data.get('start_date') or getattr(instance, 'start_date', None)
            end_date = data.get('end_date') or getattr(instance, 'end_date', None)

            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_date and end_date and end_date < start_date:
                raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})

            if start_date and start_date < date.today():
                raise serializers.ValidationError({"start_date": "Start date cannot be in the past."})

            return data
    

class ProjectInviteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    emails = serializers.ListField(child=serializers.EmailField(),required=False,write_only=True)

    class Meta:
        model = ProjectInvite
        fields = ['email', 'emails']

    def validate_email(self, value):
        project = self.context['project']

        existing_user = User.objects.filter(email=value).first()

        if project.created_by.email == value:
            raise serializers.ValidationError("You cannot invite yourself to your own project.")

        if existing_user and hasattr(existing_user, 'contributor_profile'):
            if project.members.filter(user=existing_user).exists():
                raise serializers.ValidationError("This user is already a member of the project.")
            return value
             
        if ProjectInvite.objects.filter(email=value, project=project, status='pending').exists():
            raise serializers.ValidationError("An invitation is already pending for this email.")

        return value

    def validate(self, attrs):
        # Handle both single email and list of emails
        email = attrs.get('email')
        emails = attrs.get('emails', [])
        
        if not email and not emails:
            raise serializers.ValidationError("Either 'email' or 'emails' field is required.")
        
        return attrs
    
class InviteRegisterSerializer(serializers.ModelSerializer):
    token = serializers.UUIDField(write_only=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['token', 'first_name', 'last_name', 'password', 'confirm_password']

    def validate(self, data):
        logger.debug("Validating InviteRegisterSerializer data")

        password = data.get('password')
        confirm_password = data.get('confirm_password')
        token = data.get('token')

        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            invite = ProjectInvite.objects.get(token=token)
        except ProjectInvite.DoesNotExist:
            logger.warning("Invalid or missing invitation token")
            raise serializers.ValidationError("Invalid or expired invitation token.")

        if invite.is_expired:
            invite.mark_expired()
            raise serializers.ValidationError("This invitation has expired.")
        if invite.status == "accepted":
            raise serializers.ValidationError("This invitation has already been accepted.")

        self.context['invite'] = invite
        return data

    def create(self, validated_data):
        logger.debug("Creating user from invite registration")

        invite = self.context['invite']
        email = invite.email
        password = validated_data.pop('password')
        validated_data.pop('confirm_password', None)
        validated_data.pop('token', None)

        if User.objects.filter(email=email).exists():
            logger.warning(f"User with email {email} already exists")
            raise serializers.ValidationError("User with this email already exists.")

        user = User.objects.create(email=email, role='member', **validated_data)
        user.set_password(password)
        user.save()

        contributor = Contributor.objects.create(user=user)

        invite.project.members.add(contributor)

        invite.mark_accepted()

        refresh = RefreshToken.for_user(user)

        logger.info(f"New contributor {email} registered and joined project '{invite.project.name}'")

        return {
            "email": email,
            "project": invite.project.name,
            "role":'member',
            "status": invite.status,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }
 
class TaskSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=Contributor.objects.all(), many=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'slug', 'project',
            'assigned_to',
            'title', 'description', 'due_date', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Task title cannot be empty or only spaces.")
        
        project = self.context.get('project')

        if project:
            if Task.objects.filter(
                project=project,
                title__iexact=value
            ).exclude(id=self.instance.id if self.instance else None).exists():
                raise serializers.ValidationError("A task with this title already exists in this project.")
        
        return value

    def validate(self, data):
        due_date = data.get('due_date')
        assigned_to = data.get('assigned_to', [])
        project = self.context.get('project')

        if due_date and due_date < date.today():
            raise serializers.ValidationError({"due_date": "Due date cannot be in the past."})

        if assigned_to and project:
            for contributor in assigned_to:
                if not project.members.filter(id=contributor.id).exists():
                    raise serializers.ValidationError({f"Contributor with ID {contributor.id} is not part of this project."})

        return data
class TaskListSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'slug', 'description', 'due_date', 
            'status', 'project', 'project_name', 'assigned_to',
            'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'is_overdue']
    
    def get_assigned_to(self, obj):
        return [
            {
                'id': contributor.id,
                'email': contributor.user.email,
                'name':contributor.user.first_name,
                # Add other fields you need from Contributor model
            }
            for contributor in obj.assigned_to.all()
        ]