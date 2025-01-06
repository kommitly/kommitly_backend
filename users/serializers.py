from rest_framework import serializers
from .models import User

"""
 Takes user input (like from a registration form) and converts
   it into a User object that Django can work with.
"""


# Create User serializer
class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
   
        
        }

"""Takes a User object from Django and converts it into a format (like JSON) 
 that can be easily understood and used by
   the user (like displaying user details on a webpage)."""

# User serializer
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_verified",
            "created_at",
            "updated_at",
        ]

