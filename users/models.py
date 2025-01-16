from django.db import models
from .managers import CustomUserManager
import uuid
from django.core.validators import MinLengthValidator
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string

def generate_verification_token():
    return get_random_string(50)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    first_name = models.CharField(max_length=255, db_index=True)
    last_name = models.CharField(max_length=255, db_index=True)
    full_name = None
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=50, default=generate_verification_token, null=True)  # Specify length
    profile_picture = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(validators=[MinLengthValidator(8)], max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.first_name + " " + self.last_name   
    
   