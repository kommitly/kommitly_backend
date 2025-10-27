from rest_framework import serializers
from .models import User

# Create User serializer
class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "timezone",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password'],
            timezone=validated_data["timezone"]  # Ensure this is passed
        )
        return user
    
#google user serializer
class GoogleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'is_verified', 'timezone']
    
    def create(self, validated_data):
        user = User(**validated_data)
        user.set_unusable_password()
        user.save()
        return user
    

# User serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "timezone",
            "is_verified",
            "created_at",
            "updated_at",
            "email_sent"
            ""
        ]