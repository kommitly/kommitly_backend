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
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password"],
            timezone=validated_data["timezone"],
        )
        return user

    def update(self, instance, validated_data):
        """
        Prevent direct email updates.
        Email changes must go through verification flow.
        """
        validated_data.pop("email", None)
        validated_data.pop("password", None)

        return super().update(instance, validated_data)

    
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
            "email_sent",
            "last_active"
            
        ]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="The email address of the user.")

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="The reset token received via email.")
    password = serializers.CharField(required=True, min_length=8, help_text="The new password.")