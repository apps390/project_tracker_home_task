from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import random
from datetime import timedelta
from django.utils import timezone



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
    ('manager', 'Project Manager'),
    ('member', 'Team Member'),
   ]
    username = None
    email = models.EmailField(unique=True, blank=False, null=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    




class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self, minutes=5):
        """OTP valid if not used and within `minutes` from creation."""
        return (not self.is_used) and (timezone.now() < self.created_at + timedelta(minutes=minutes))

    @staticmethod
    def generate_otp():
        return f"{random.randint(100000, 999999):06d}"

    def mark_used(self):
        self.is_used = True
        self.save()

