import logging
from urllib.parse import urlencode
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_yasg import openapi
from .serializers import CreateUserSerializer, UserSerializer, GoogleUserSerializer
import kommitly_backend.settings as st
from drf_yasg.utils import swagger_auto_schema
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import AccessToken
from .models import User, generate_verification_token, UserActivity
from timezonefinder import TimezoneFinder
from django.utils import timezone
from datetime import timedelta
import traceback
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from django.contrib.auth import get_user_model
from goals.models import Goal, AiGoal, Task, AiTask
from collections import Counter
from users.tasks import send_verification_email

user = get_user_model()



#Configure logging
logger = logging.getLogger(__name__)







class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["User"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["id_token"],
            properties={
                "id_token": openapi.Schema(type=openapi.TYPE_STRING, format="id_token"),
            },
        ),
        responses={
            200: UserSerializer,
            400: "Bad Request",
            401: "Unauthorized",
        },
        operation_description="Authenticate user with Google ID token",
    )
    def post(self, request, *args, **kwargs):
        id_token_str = request.data.get("id_token")
        if not id_token_str:
            return Response({"error": "ID token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 1: Verify the ID token
            idinfo = id_token.verify_oauth2_token(id_token_str, Request(), st.GOOGLE_CLIENT_ID)

            # Step 2: Extract user details
            email = idinfo.get("email")
            first_name = idinfo.get("given_name")
            last_name = idinfo.get("family_name")

            if not email:
                return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Step 3: Check if user exists or create one
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user_data = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": email.split('@')[0],
                    "is_verified": True,
                    "timezone": "UTC",
                }

                serializer = GoogleUserSerializer(data=user_data)
                serializer.is_valid(raise_exception=True)
                user = serializer.save()

            # Step 4: Generate tokens for both existing and new users
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            return Response({
                "message": "Login successful",
                "refresh": str(refresh),
                "access": str(access),
                "user": UserSerializer(user).data,
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid ID token: {str(e)}")
            return Response({"error": "Invalid ID token."}, status=status.HTTP_401_UNAUTHORIZED)

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
                    timezone = validated_data["timezone"],
                    is_verified=False,
                

                )

                # Hash password
                user.set_password(validated_data["password"])
                user.verification_token = generate_verification_token() #Generate token here.
                user.save()
      
                send_verification_email(user)

                # Refresh from DB to get the updated email_sent status for the response
                user.refresh_from_db()


              
                user_data= UserSerializer(user).data
                logger.debug(f"User created {user}. Email sent: {user.email_sent}")
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



class VerifyUserView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            200: "User verified successfully",
            400: "Invalid token",
            404: "User not found",
        },
        operation_description="Verify a User's account via token",
    )
    def get(self, request, token, *args, **kwargs):
        """
        Verify a user using a unique token.
        """
        
        user = User.objects.filter(verification_token=token).first()

        if not user:
            return Response({"error": "Invalid or expired verification token."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return redirect("https://kommitly-frontend.vercel.app/dashboard")

        user.is_verified = True
        user.verification_token = None  # Clear the token after verification
        user.save()


        
        
       
                
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # 🔁 Redirect with tokens as query params
        query_params = urlencode({
            "access": str(access),
            "refresh": str(refresh),
        })
        redirect_url = f"https://kommitly-frontend.vercel.app/verify-redirect?{query_params}"
        return redirect(redirect_url)

class CheckVerificationStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            200: "Verification status returned",
            404: "User not found",
        },
        operation_description="Check if a user is verified using their email",
    )
    def get(self, request, email, *args, **kwargs):
        """
        Check if a user is verified using their email.
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                f"User with email {email} not found",
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = {"verified": user.is_verified}

        if user.is_verified:
            # Generate a new access token for the verified user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            response_data["token"] = access_token

        return Response(response_data, status=status.HTTP_200_OK)


class LoginUserView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["User"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={
            200: "Login successful",
            400: "Bad request",
            401: "User not verified",
            404: "User not found",
        },
        operation_description="Login a User",
    )
    def post(self, request, *args, **kwargs):
        """
        Login a user (only verified users)
        """
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if the user is verified
        if not user.is_verified:
            

            # regenerate token only if needed
            if not user.verification_token:
                user.verification_token = generate_verification_token()
                user.save(update_fields=['verification_token'])

            send_verification_email(user)

            return Response(
                    {"error": "User account is not verified. A verification email has been sent."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
     
            
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Record login activity
        UserActivity.objects.create(
            user=user,
            activity_type="login",
            metadata={
                "ip": request.META.get('REMOTE_ADDR'),
                "user_agent": request.META.get('HTTP_USER_AGENT'),
            },
        )

        return Response(
            {
                "message": "Login successful",
                "refresh": str(refresh),
                "access": str(access),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )



# Get user details
class GetUserView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    @swagger_auto_schema(
        tags=["User"],
        responses={200: UserSerializer, 404: "Not Found"},
        operation_description="Get user by email",
    )
    def get(self, request, email, *args, **kwargs):
        """
        Get a user by email
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                f"User with email {email} not found",
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)



# Update user with email
class UpdateUserByEmailView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    @swagger_auto_schema(
        tags=["User"],
        request_body=CreateUserSerializer,
        responses={
            200: UserSerializer,
            400: "Validation Error",
            404: "Not Found",
            500: "Unexpected Error",
        },
        operation_description="Update User by email",
    )
    def patch(self, request, email, *args, **kwargs):
        """
        Update a user by email
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreateUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                updated_user = serializer.save()
                logger.debug(f"Updated user: {updated_user}")
                return Response(
                    UserSerializer(updated_user).data, status=status.HTTP_200_OK
                )
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Update user with token
class UpdateAuthenticatedUserView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @swagger_auto_schema(
        tags=["User"],
        request_body=CreateUserSerializer,
        responses={
            200: UserSerializer,
            400: "Validation Error",
            404: "Not Found",
            500: "Unexpected Error",
        },
        operation_description="Update authenticated User",
    )
    def patch(self, request, *args, **kwargs):
        """
        Update a user by token
        """
        try:
            user = User.objects.get(email=request.user.email)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {request.user.email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreateUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                updated_user = serializer.save()
                logger.debug(f"Updated user: {updated_user}")
                return Response(
                    UserSerializer(updated_user).data, status=status.HTTP_200_OK
                )
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





#Delete authenticated user
class DeleteAuthenticatedUserView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            204: "No Content", 
            404: "Not Found",
            500: "Unexpected Error",
        },
        operation_description="Delete authenticated user",
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete authenticated user
        """
        try:
            user = User.objects.get(email=request.user.email)
            user.delete()
            logger.debug(f"User with email {user.email} deleted successfully")
            return Response(f"User with email {user.email} deleted successfully",status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {request.user.email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.error(f"Unexpected error: {e}\n{traceback_str}")
            return Response(
                {"error": f"An error occurred while deleting the user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


#Delete user by email
class DeleteUserByEmailView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            204: "No Content", 
            404: "Not Found",
            500: "Unexpected Error",
        },
        operation_description="Delete user by email",
    )
    def delete(self, request, email, *args, **kwargs):
        """
        Delete user by email
        """
        try:
            user = User.objects.get(email=email)
            user.delete()
            logger.debug(f"User with email {user.email} deleted successfully")
            return Response(f"User with email {user.email} deleted successfully",status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class GetTimezoneView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Determine and update the user's timezone based on lat/lng.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["latitude", "longitude"],
            properties={
                "latitude": openapi.Schema(type=openapi.TYPE_NUMBER),
                "longitude": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
        responses={200: openapi.Response("Timezone updated")},
        tags=["User"],
    )
    def post(self, request):
        try:
            latitude = request.data.get("latitude")
            longitude = request.data.get("longitude")

            tf = TimezoneFinder()
            timezone = tf.timezone_at(lat=latitude, lng=longitude)

            if timezone:
                request.user.timezone = timezone
                request.user.save()
                return Response({"timezone": timezone}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Could not determine timezone"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Dashboard"],
        operation_description="Retrieve all dashboard statistics for the authenticated user.",
        responses={
            200: openapi.Response(
                description="Dashboard stats retrieved successfully",
                examples={
                    "application/json": {
                        "goal_progress": [{"goal": "Health", "progress": 0.5}],
                        "tasks_completed_today": {"count": 2, "titles": ["Task A", "Task B"]},
                        "tasks_completed_week": {"count": 10, "titles": []},
                        "ai_tasks_completed_today": {"count": 1, "titles": ["AI Task"]},
                        "ai_tasks_completed_week": {"count": 4, "titles": []},
                        "current_streak": 3,
                        "longest_streak": 7,
                        "recent_activity_summary": {"2025-02-20": 4},
                        "recent_goal_updates": [],
                        "top_tags": [["work", 5]],
                        "least_tags": [["fitness", 1]],
                        "popular_tags": [["school", 7]]
                    }
                }
            ),
            401: "Unauthorized",
            500: "Unexpected Error"
        }
    )





    def get(self, request):
        user = request.user
        now = timezone.now()

        # 1️⃣ Goals & AI Goals progress
        user_goals = Goal.objects.filter(user=user)
        ai_goals = AiGoal.objects.filter(user=user)

        goal_progress = [
            {"goal": g.title, "progress": g.progress / 100}  # normalize to 0-1 for frontend charts
            for g in list(user_goals) + list(ai_goals)
        ]
        
        # 2️⃣ Tasks & AI Tasks completed today / this week (with titles)
        today = now.date()
        week_start = today - timedelta(days=today.weekday())

        tasks_today_qs = Task.objects.filter(user=user, completed_at__date=today)
        tasks_week_qs = Task.objects.filter(user=user, completed_at__date__gte=week_start)

        ai_tasks_today_qs = AiTask.objects.filter(ai_goal__user=user, completed_at__date=today)
        ai_tasks_week_qs = AiTask.objects.filter(ai_goal__user=user, completed_at__date__gte=week_start)

        tasks_completed_today = {
            "count": tasks_today_qs.count(),
            "titles": list(tasks_today_qs.values_list("title", flat=True))
        }
        tasks_completed_week = {
            "count": tasks_week_qs.count(),
            "titles": list(tasks_week_qs.values_list("title", flat=True))
        }
        ai_tasks_completed_today = {
            "count": ai_tasks_today_qs.count(),
            "titles": list(ai_tasks_today_qs.values_list("title", flat=True))
        }
        ai_tasks_completed_week = {
            "count": ai_tasks_week_qs.count(),
            "titles": list(ai_tasks_week_qs.values_list("title", flat=True))
        }

        # 3️⃣ Activity streak / consistency
        activity_logs = UserActivity.objects.filter(user=user).order_by('timestamp')
        streak = 0
        max_streak = 0
        last_day = None
        for log in activity_logs:
            log_day = log.timestamp.date()
            if last_day:
                if (log_day - last_day).days == 1:
                    streak += 1
                elif (log_day - last_day).days > 1:
                    streak = 1
            else:
                streak = 1
            max_streak = max(max_streak, streak)
            last_day = log_day

        # 4️⃣ Recent activity summary (last 7 days)
        recent_activity_qs = UserActivity.objects.filter(user=user, timestamp__gte=now - timedelta(days=7))
        activity_summary = {}
        recent_goal_updates = []

        for act in recent_activity_qs:
            day = act.timestamp.strftime("%Y-%m-%d")
            activity_summary[day] = activity_summary.get(day, 0) + 1

            if act.activity_type in ["goal_updated", "ai_goal_updated", "task_updated", "ai_task_updated", "ai_subtask_updated"]:
                recent_goal_updates.append({
                    "type": act.activity_type,
                    "metadata": act.metadata,
                    "timestamp": act.timestamp
                })

        # 5️⃣ Top / least performing tags
        # Top-performing: tags from completed tasks/goals
        completed_tasks = Task.objects.filter(user=user, completed_at__isnull=False)
        completed_ai_tasks = AiTask.objects.filter(ai_goal__user=user, completed_at__isnull=False)

        # Flatten all tags
        completed_tags = list(completed_tasks.values_list("tag", flat=True)) + \
                         list(completed_ai_tasks.values_list("ai_goal__tag", flat=True))

        top_tags = Counter([t for t in completed_tags if t]).most_common(5)  #total number of completed Tasks and completed AI Tasks that were assigned that specific tag.

        # Least-performing: tags from overdue tasks (tasks with due_date < now and not completed)
        overdue_tasks = Task.objects.filter(user=user, completed_at__isnull=True, due_date__lt=now)
        overdue_ai_tasks = AiTask.objects.filter(ai_goal__user=user, completed_at__isnull=True, due_date__lt=now)

        overdue_tags = list(overdue_tasks.values_list("tag", flat=True)) + \
                       list(overdue_ai_tasks.values_list("ai_goal__tag", flat=True))

        least_tags = Counter([t for t in overdue_tags if t]).most_common()[-5:]  # 5 the total number of overdue Tasks and overdue AI Goals/Tasks that were assigned that specific tag. least perfoming

        # Popular tags: tags that appear most in activity logs
        activity_tags = []
        for act in activity_logs:
            if act.metadata and "tags" in act.metadata:
                activity_tags.extend(act.metadata["tags"])

        popular_tags = Counter(activity_tags).most_common(5)  #the total number of activity logs (e.g., goal updates, task updates) that included that specific tag in their metadata.

        return Response({
            "goal_progress": goal_progress,
            "tasks_completed_today": tasks_completed_today,
            "tasks_completed_week": tasks_completed_week,
            "ai_tasks_completed_today": ai_tasks_completed_today,
            "ai_tasks_completed_week": ai_tasks_completed_week,
            "current_streak": streak,
            "longest_streak": max_streak,
            "recent_activity_summary": activity_summary,
            "recent_goal_updates": recent_goal_updates,
            "top_tags": top_tags,
            "least_tags": least_tags,
            "popular_tags": popular_tags,
        })
