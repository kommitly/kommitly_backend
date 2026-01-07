from django.db import models
from .managers import CustomUserManager
import uuid
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
import pytz
from django.utils import timezone
from django.utils import timezone as dj_timezone
from datetime import timedelta


def generate_verification_token():
    return get_random_string(50)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    first_name = models.CharField(max_length=255, db_index=True)
    last_name = models.CharField(max_length=255, db_index=True)
    full_name = None
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    pending_email = models.EmailField(
        max_length=255, null=True, blank=True, db_index=True
    )
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=50, default=generate_verification_token, null=True)  # Specify length
    profile_picture = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(validators=[MinLengthValidator(8)], max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in pytz.all_timezones], default='UTC')  # Add timezone field
    email_sent = models.BooleanField(default=False)
    token_created_at = models.DateTimeField(null=True, blank=True)
    last_active = models.DateTimeField(default=dj_timezone.now)
    password_reset_token = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)




    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "timezone", "password"]

    def __str__(self):
        return self.first_name + " " + self.last_name   

    def is_token_valid(self):
        if not self.token_created_at:
            return False
        # Token expires in 24 hours
        return timezone.now() < self.token_created_at + timedelta(hours=24)

    def is_reset_token_valid(self):
        if not self.password_reset_token or not self.password_reset_sent_at:
            return False
        # Password reset tokens should be shorter-lived (usually 1 hour)
        return timezone.now() <= self.password_reset_sent_at + timedelta(hours=1)

    # 3. HELPER TO CLEAR TOKEN (Optional but recommended)
    def clear_reset_token(self):
        self.password_reset_token = None
        self.password_reset_sent_at = None
        self.save(update_fields=['password_reset_token', 'password_reset_sent_at'])
    


class UserActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, default='login')  # e.g., login, goal_update, task_complete
    metadata = models.JSONField(blank=True, null=True)  # optional: store context like {"page": "dashboard", "device": "mobile"}
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} active at {self.timestamp}"
   