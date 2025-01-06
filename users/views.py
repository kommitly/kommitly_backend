import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import User
from .serializers import CreateUserSerializer, UserSerializer
import kommitly_backend.settings as st
from drf_yasg.utils import swagger_auto_schema
from django.core.exceptions import ValidationError


#Configure logging
logger = logging.getLogger(__name__)


# Create user
class CreateUserView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]
    @swagger_auto_schema(
        tags= ["User"],
        request_body=CreateUserSerializer,
        responses={
            201: UserSerializer,
            400: "Validation error",
            500: "Unexpected error",       
        },
        operation_description="Register a User",
    )
    def post (self, request, *args, **kwargs):
        """
        Create a new user
        """
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try: 
                validated_data = serializer.validated_data
                user = User(
                    first_name = validated_data["first_name"],
                    last_name = validated_data["last_name"],
                    email = validated_data["email"],

                )

                # Hash password
                user.set_password(validated_data["password"])
                user.save()
                user_data= UserSerializer(user).data
                logger.debug(f"User created {user}")
                return Response(user_data, status=status.HTTP_201_CREATED)
            # Catches validation errors. This is used to handle unexpected validation errors that might occur during other parts of the code execution, not just during serializer validation.
            except ValidationError as e:
                logger.error(f"Validation error {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            # Catches any other unexpected errors
            except Exception as e:
                logger.error(f"Unexpexted error {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # If the serializer is not valid, return a 400 error
        else: 
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
   

