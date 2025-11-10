from django.db import models
from project_tracker.utils.create_unique_slug import  generate_secure_slug
from project_tracker import settings
from datetime import timedelta
from django.utils import timezone
import uuid


class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('overdue', 'Overdue'),
    ]

    name = models.CharField(max_length=200,db_index=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True,blank=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='created_projects')
    start_date = models.DateField()
    end_date = models.DateField()
    members = models.ManyToManyField('Contributor',related_name='projects',blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_secure_slug(self, 'name')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Contributor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='contributor_profile')
    skills = models.JSONField(default=list, blank=True)
    joined_on = models.DateField(auto_now_add=True)

   
    def __str__(self):
        return f"Contributor: {self.user.email}"
    
def default_expiry():
    return timezone.now() + timedelta(days=2)


class ProjectInvite(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
    ]

    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='invites')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invites')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    def __str__(self):
        return f"Invite for {self.email} to {self.project.name}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_accepted(self):
        self.status = "accepted"
        self.save(update_fields=["status"])

    def mark_expired(self):
        self.status = "expired"
        self.save(update_fields=["status"])


class Task(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    project = models.ForeignKey('Project',on_delete=models.CASCADE,related_name='tasks')
    assigned_to = models.ManyToManyField('Contributor', blank=True,related_name='tasks')
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_secure_slug(self, 'title')
        if self.status != 'completed' and self.due_date < timezone.now().date():
            self.status = 'overdue'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.project.name})"