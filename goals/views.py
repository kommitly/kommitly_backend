import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, time, date
from django.utils import timezone
import pytz
from rest_framework import status, permissions, generics
from .models import Goal, Task, AiGoal, AiTask, SubTask, AiSubTask, Routine, DailyActivity, Template, DailyActivityHistory
from .serializers import GoalSerializer, TaskSerializer, CreateGoalSerializer, CreateTaskSerializer, CreateAiTaskSerializer,AiGoalSerializer, AiTaskSerializer, CreateAiGoalSerializer, UserProfileSerializer, UpdateAiGoalSerializer, SubTaskSerializer, AiSubTaskSerializer, RoutineSerializer,TemplateSerializer, DailyActivitySerializer, DailyActivityHistorySerializer
import kommitly_backend.settings as st
from drf_yasg.utils import swagger_auto_schema
from django.core.exceptions import ValidationError
from ai_insights.utils import get_insights, answer_subtask_question, answer_task_question, ai_generate_tag_and_emoji
from drf_yasg import openapi
from users.models import User
from django.http import Http404
from django.db.models import Prefetch
from .tasks import send_task_reminders
from django.db.models import Q
from .constants import FIXED_ACTIVITIES
from django.core.management import call_command
from django.conf import settings
from users.utils import log_activity



# Configure logging
logger = logging.getLogger(__name__)

"""
# Create your views here.
class CreateGoalWithAIInsightsView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=CreateAiGoalSerializer,
        responses={
            201: openapi.Response(
                description="Goal created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ai_goal": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            }
                        ),
                        "ai_tasks": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'ai_goal': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'completed_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                }
                            )
                        ),
                    },
                ),
            ),
            400: "Validation error",
            500: "Unexpected error",
        },
        operation_description="Register a Goal and get AI insights",
    )
    def post(self, request):

        user = request.user
        if not user.is_verified:  # Assuming 'verified' is a field in the User model
            return Response({"error": "User is not verified."}, status=status.HTTP_403_FORBIDDEN)


        # Deserialize the goal data
        goal_serializer = CreateAiGoalSerializer(data=request.data, context={"request": request})
        
        if goal_serializer.is_valid():
            # Save the goal to the database
            ai_goal = goal_serializer.save()

            try:
                # Call AI insights utility to get actionable steps
                insights = get_insights(ai_goal.title)

                # Print the insights for debugging
                print("Goal Title:", ai_goal.title)
                print("Insights:", insights)

                if not insights:
                    return Response({"error": "No insights returned from AI service."}, status=status.HTTP_400_BAD_REQUEST)

                # Generate tasks from insights
                ai_tasks = []
                for step in insights:
                    task_data = {
                        "ai_goal": ai_goal.id,
                        "title": step.get("task_title"),
                        "due_date": None,  # Handle missing due_date
                        "status": "pending",
                        "actionable_steps": step.get("actionable_steps"),  # Include actionable steps
                        "task_timeline": step.get("task_timeline")  # Include task timeline
                    }
                    task_serializer = AiTaskSerializer(data=task_data)
        
                    if task_serializer.is_valid():
                        task = task_serializer.save()
                        ai_tasks.append(task)
                    else:
                        return Response(task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # Prepare response data
                response_data = {
                    "ai_goal": AiGoalSerializer(ai_goal).data,
                    "ai_tasks": AiTaskSerializer(ai_tasks, many=True).data,
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": f"An error occurred while generating insights: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(goal_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
"""


# Generate AI insights without storing the goal
class GenerateAIInsightsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=CreateAiGoalSerializer,
        responses={
            200: openapi.Response(
                description="AI insights generated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ai_goal": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'category': openapi.Schema(type=openapi.TYPE_STRING),
                                'progress': openapi.Schema(type=openapi.TYPE_STRING),
                                'tag': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),  # Added tag field
                            }
                        ),
                        "ai_tasks": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'task_timeline': openapi.Schema(type=openapi.TYPE_STRING),
                                    'ai_subtasks': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                                'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                        )
                                    ),
                                }
                            )
                        ),
                    },
                ),
            ),
            400: "Validation error",
            500: "Unexpected error",
        },
        operation_description="Generate AI insights without storing the goal",
    )
    def post(self, request):
        user = request.user
        if not user.is_verified:  # Assuming 'verified' is a field in the User model
            return Response({"error": "User is not verified."}, status=status.HTTP_403_FORBIDDEN)

        # Deserialize the goal data
        goal_serializer = CreateAiGoalSerializer(data=request.data, context={"request": request})
        
        if goal_serializer.is_valid():
            goal_data = goal_serializer.validated_data

            try:
                # Call AI insights utility to get actionable steps
                insights = get_insights(goal_data['description'])

                # Print the insights for debugging
                print("Goal Title:", goal_data['title'])
                print("Insights:", insights)
            

                if not insights:
                    return Response({"error": "No insights returned from AI service."}, status=status.HTTP_400_BAD_REQUEST)

                # Generate tasks from insights
                ai_tasks = []
                for step in insights.get("tasks", []): 
                    ai_subtasks = [
                        {
                            "title": ai_subtask.get("subtask_title"),
                            "description": ai_subtask.get("description"),
                            "due_date": ai_subtask.get("due_date"),
                            "status": "pending"
                        }
                        for ai_subtask in step.get("ai_subtasks", [])
                    ]
                    task_data = {
                        "title": step.get("task_title"),
                        "due_date": None,
                        "status": "pending",
                        "task_timeline": step.get("task_timeline"),
                        "ai_subtasks": ai_subtasks  
                    }
                    ai_tasks.append(task_data)

                # Prepare response data
                response_data = {
                    "ai_goal": {
                        "title": insights.get("goal_title", goal_data['title']),
                        "description": goal_data['description'],
                        "tag": insights.get('goal_tag', 'No Tag'),  # Include tag if provided
                        "category": insights.get("goal_category", "Uncategorized"), 
                        "progress": goal_data.get('progress', "0"),
                    },
                    "ai_tasks": ai_tasks,
                  
                }
                return Response(response_data, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({"error": f"An error occurred while generating insights: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(goal_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Create goal with AI insights and store in the database
class CreateGoalWithAIInsightsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "ai_goal": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                        'category': openapi.Schema(type=openapi.TYPE_STRING),
                        'progress': openapi.Schema(type=openapi.TYPE_STRING),
                        
                        
                    }
                ),
                "ai_tasks": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'title': openapi.Schema(type=openapi.TYPE_STRING),
                            'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'task_timeline': openapi.Schema(type=openapi.TYPE_STRING),



                            'ai_subtasks': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                                'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                        )
                                    ),
                        }
                    )
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Goal created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ai_goal": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            }
                        ),
                        "ai_tasks": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'ai_goal': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'due_date': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'overdue_reason': openapi.Schema(type=openapi.TYPE_STRING),
                                    "task_timeline": openapi.Schema(type=openapi.TYPE_STRING),
                                    'completed_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    'reminder_sent': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'reminder_time': openapi.Schema(type=openapi.TYPE_STRING, format='time'),
                                    'last_updated': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    "ai_subtasks": openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "title": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                "due_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True),
                                                "status": openapi.Schema(type=openapi.TYPE_STRING),
                                                'overdue_reason': openapi.Schema(type=openapi.TYPE_STRING),
                                                'completed_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                'reminder_sent': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                                'reminder_time': openapi.Schema(type=openapi.TYPE_STRING, format='time'),
                                                'last_updated': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                            }
                                        )
                                    ),
                                }
                            )
                        ),
                    },
                ),
            ),
            400: "Validation error",
            500: "Unexpected error",
        },
        operation_description="Register a Goal and get AI insights",
    )
    def post(self, request):
        user = request.user
        if not user.is_verified:  # Assuming 'verified' is a field in the User model
            return Response({"error": "User is not verified."}, status=status.HTTP_403_FORBIDDEN)

        # Extract goal and tasks from request data
        ai_goal_data = request.data.get('ai_goal')
        ai_tasks_data = request.data.get('ai_tasks')

        if not ai_goal_data or not ai_tasks_data:
            return Response({"error": "AI goal and tasks are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Deserialize the goal data
        goal_serializer = CreateAiGoalSerializer(data=ai_goal_data, context={"request": request})
        
        
        if goal_serializer.is_valid():
            # Save the goal to the database
            ai_goal = goal_serializer.save(user=user)

            try:
                # Save tasks to the database
                ai_tasks = []
                print(f"AI tasks data: {ai_tasks_data}")
                for task_data in ai_tasks_data:
                    task_data['ai_goal'] = ai_goal.id
                    subtasks_data = task_data.pop("ai_subtasks", [])
                    print(f"Task data: {subtasks_data}")

                    task_serializer = AiTaskSerializer(data=task_data)


                    if task_serializer.is_valid():
                        task = task_serializer.save()
                        ai_tasks.append(task)

                        
                       
                        for subtask_data in subtasks_data:
                            subtask_data["ai_task"] = task.id
                            print(f"Subtask data: {subtask_data}")
                            subtask_serializer = AiSubTaskSerializer(data=subtask_data, context = {"ai_task_id":task.id}) # pass the current task id to the subtask serializer.


                            if subtask_serializer.is_valid():
                                subtask_serializer.save()
                            else:
                                return Response(subtask_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    else:
                        return Response(task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # Prepare response data
                response_data = {
                    "ai_goal": AiGoalSerializer(ai_goal).data,
                 
                }



                return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": f"An error occurred while saving tasks: {str(e)}", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        return Response(goal_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CreateGoalView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags= ["Goals"],
        request_body=CreateGoalSerializer,
        responses={
            201: GoalSerializer,
            400: "Validation error",
            500: "Unexpected error",       
        },
        operation_description="Register a Goal",
    )

    def post(self, request):
        data = request.data.copy()

        # If tag or emoji missing → use AI classifier
        if not data.get("tag") or not data.get("emoji"):
            ai_result = ai_generate_tag_and_emoji(data.get("title"))
            data["tag"] = ai_result.get("tag")
            data["emoji"] = ai_result.get("emoji")

        serializer = CreateGoalSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            goal = serializer.save()
            return Response(GoalSerializer(goal).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        
 
class CreateTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags= ["Tasks"],
        request_body=CreateTaskSerializer,
        responses={
            201: TaskSerializer,
            400: "Validation error",
            500: "Unexpected error",
        },
        operation_description="Register a Task",
    )
    



    def post(self, request):
        data = request.data.copy()

        # If tag or emoji missing → use AI classifier
        if not data.get("tag") or not data.get("emoji"):
            ai_result = ai_generate_tag_and_emoji(data.get("title"))
            data["tag"] = ai_result.get("tag")
            data["emoji"] = ai_result.get("emoji")

        serializer = CreateTaskSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            task = serializer.save()
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

        logger.error(f"Task creation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Update goal
class UpdateGoalByEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["Goals"],
        request_body=GoalSerializer,
        responses={
            200: GoalSerializer,
            400: "Validation error",
            404: "Not Found",
            500: "Unexpected error",
        },
        operation_description="Update a Goal By email",
    )
    def patch(self, request, *args, **kwargs):
        # Extract email and id from kwargs
        email = kwargs.get('email')
        goal_id = kwargs.get('id')

        # Validate email and goal_id
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not goal_id:
            return Response({"error": "Goal ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch user by email
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Fetch goal by ID and user
            goal = Goal.objects.get(id=goal_id, user=user)
        except Goal.DoesNotExist:
            return Response(
                {"error": f"Goal with ID {goal_id} for user {email} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update goal using serializer
        serializer = GoalSerializer(goal, data=request.data, partial=True)
        if serializer.is_valid():
            updated_goal = serializer.save()
            return Response(GoalSerializer(updated_goal).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Update authenticated goal
class UpdateAuthenticatedGoalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Goals"],
        request_body=GoalSerializer,
        responses={
            200: GoalSerializer,
            400: "Validation error",
            404: "Not Found",
            500: "Unexpected error",
        },
        operation_description="Update Authenticated Goal",
    )
    def patch(self, request, *args, **kwargs):
        # Extract email and id from kwargs
       
        goal_id = kwargs.get('id')

        # Validate  and goal_id
        if not goal_id:
            return Response({"error": "Goal ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch user by email
            user = User.objects.get(email=request.user.email)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {request.user.email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Fetch goal by ID and user
            goal = Goal.objects.get(id=goal_id, user=user)
        except Goal.DoesNotExist:
            return Response(
                {"error": f"Goal with ID {goal_id} for user {request.user.email} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update goal using serializer
        serializer = GoalSerializer(goal, data=request.data, partial=True)
        if serializer.is_valid():
            updated_goal = serializer.save()

            log_activity(
                request.user,
                "goal_updated",
                {
                    "goal_id": updated_goal.id,
                    "title": updated_goal.title,
                    "tags": [updated_goal.tag] if updated_goal.tag else []
                }
            )

            return Response(GoalSerializer(updated_goal).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Update authenticated Ai goal
class UpdateAuthenticatedAiGoalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=UpdateAiGoalSerializer,
        responses={
            200: AiGoalSerializer,
            400: "Validation error",
            404: "Not Found",
            500: "Unexpected error",
        },
        operation_description="Update Authenticated Ai Goal",
    )

    def patch(self, request, *args, **kwargs):
        goal_id = kwargs.get('id')

        if not goal_id:
            return Response({"error": "Goal ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=request.user.email)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with email {request.user.email} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ai_goal = AiGoal.objects.get(id=goal_id, user=user)
        except AiGoal.DoesNotExist:
            return Response(
                {"error": f"Goal with ID {goal_id} for user {request.user.email} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update only the title and description of the goal
        serializer = UpdateAiGoalSerializer(ai_goal, data=request.data, partial=True)
        if serializer.is_valid():
            updated_goal = serializer.save()

           log_activity(
                request.user,
                "ai_goal_updated",
                {
                    "goal_id": updated_ai_goal.id,
                    "title": updated_ai_goal.title,
                    "tags": [updated_ai_goal.tag] if updated_ai_goal.tag else []
                }
            )

            return Response(AiGoalSerializer(updated_goal).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserAuthenticatedProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            200: "User profile with goals and tasks",
            401: "Unauthorized",
        },
        operation_description="Fetch the authenticated user's profile with their goals and tasks",
    )
    def get(self, request, *args, **kwargs):
        try:
            user = request.user

            # Fetch the user's goals
            goals = Goal.objects.filter(user=user)
            goal_serializer = GoalSerializer(goals, many=True)

            ai_goals = AiGoal.objects.filter(user=user)
            ai_goal_serializer = AiGoalSerializer(ai_goals, many=True)

            # Fetch the user's tasks (if tasks are separate and relate to goals)
            tasks = Task.objects.filter(user=user)
            task_serializer = TaskSerializer(tasks, many=True)

            ai_tasks = AiTask.objects.filter(ai_goal__user=user)  # Assuming tasks are related to goals
            ai_task_serializer = AiTaskSerializer(ai_tasks, many=True)

            # Build the response
            response_data = {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "timezone": user.timezone
                },
                "goals": goal_serializer.data,
                "tasks": task_serializer.data,
                "ai_goals": ai_goal_serializer.data,
                "ai_tasks": ai_task_serializer.data,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "An error occurred while fetching the user profile", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateAuthenticatedTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        request_body=TaskSerializer,
        responses={
            200: TaskSerializer,
            400: "Validation error",
            404: "Task not found",
            500: "Unexpected error",
        },
        operation_description="Update a task for the authenticated user",
    )
    def patch(self, request, *args, **kwargs):
        task_id = kwargs.get("id")  # Extract task ID from URL
        logger.debug(f"Task ID from URL: {task_id}")  # Debugging line
        logger.debug(f"Request data: {request.data}")  # Debugging line
       
        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Fetch the task that belongs to the authenticated user
            task = Task.objects.get(id=task_id, user=request.user) # Filter by user
            logger.debug(f"Task found: {task}")  # Debugging line
          
        except Task.DoesNotExist:
            return Response({"error": "Task not found or does not belong to the user."}, status=status.HTTP_404_NOT_FOUND)
        
        # Update task using serializer
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            updated_task = serializer.save()

            log_activity(
                request.user,
                "task_updated",
                {
                    "task_id": updated_task.id,
                    "title": updated_task.title,
                    "goal_id": updated_task.goal_id,
                    "tags": list(
                        filter(
                            None,
                            [updated_task.tag, updated_task.goal.tag if updated_task.goal else None]
                        )
                    )
                }
            )

            return Response(TaskSerializer(updated_task).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateAuthenticatedAiTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Ai Tasks"],
        request_body=AiTaskSerializer,
        responses={
            200: AiTaskSerializer,
            400: "Validation error",
            404: "Task not found",
            500: "Unexpected error",
        },
        operation_description="Update a task for the authenticated user",
    )


    def patch(self, request, *args, **kwargs):
        task_id = kwargs.get("id")  # Extract task ID from URL
        logger.debug(f"Task ID from URL: {task_id}")  # Debugging line
        logger.debug(f"Request data: {request.data}")  # Debugging line

        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the task that belongs to the authenticated user
            ai_task = AiTask.objects.get(id=task_id)
            logger.debug(f"Task found: {ai_task}")  # Debugging line
        except AiTask.DoesNotExist:
            return Response({"error": "Task not found or does not belong to the user."}, status=status.HTTP_404_NOT_FOUND)

        # Debugging: Log request data
        print("Received request data:", request.data)

        # Update task using serializer
        serializer = AiTaskSerializer(ai_task, data=request.data, partial=True)
        if serializer.is_valid():
            updated_task = serializer.save()

           
            log_activity(
                user=request.user,
                activity_type="ai_task_updated",
                metadata={
                    "task_id": updated_task.id,  # using updated_task
                    "updated_fields": list(request.data.keys()),
                    "goal_id": updated_task.ai_goal.id if hasattr(updated_task, "ai_goal") else None,
                    "tags": list(
                        filter(
                            None,
                            [updated_task.ai_goal.tag if updated_task.ai_goal else None]
                        )
                    )
                }
            )


            return Response(AiTaskSerializer(updated_task).data, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetGoalByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Goals"],
        responses={
            200: GoalSerializer,
            404: "Goal not found",
            401: "Unauthorized",
        },
        operation_description="Fetch a goal by its ID"
    )
    def get(self, request, goal_id, *args, **kwargs):
        try:
            # Fetch the goal by ID
            goal = Goal.objects.get(id=goal_id)

            # Check if the goal belongs to the authenticated user
            if goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to access this goal."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Serialize the goal data
            goal_serializer = GoalSerializer(goal)
            return Response(goal_serializer.data, status=status.HTTP_200_OK)

        except Goal.DoesNotExist:
            raise Http404("Goal not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetAiGoalByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        responses={
            200: AiGoalSerializer,
            404: "Goal not found",
            401: "Unauthorized",
        },
        operation_description="Fetch a goal by its ID"
    )
    def get(self, request, goal_id, *args, **kwargs):
        try:
            # Fetch the goal by ID with prefetch and ordering by id
            ai_goal = AiGoal.objects.prefetch_related(
                Prefetch(
                    'ai_tasks',
                    queryset=AiTask.objects.order_by('id')  # Order by id
                )
            ).get(id=goal_id)

            # Check if the goal belongs to the authenticated user
            if ai_goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to access this goal."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # ✅ Update progress before serialization
            ai_goal.update_progress()

            # Serialize the goal data
            goal_serializer = AiGoalSerializer(ai_goal)
            return Response(goal_serializer.data, status=status.HTTP_200_OK)

        except AiGoal.DoesNotExist:
            raise Http404("Goal not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )




class GetTaskByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            200: TaskSerializer,
            404: "Task not found",
            401: "Unauthorized",
        },
        operation_description="Fetch a task by its ID"
    )

    def get(self, request, task_id, *args, **kwargs):
        try:
            # Fetch the task by ID
            task = Task.objects.get(id=task_id)

            # Check if the task belongs to the authenticated user
            if task.goal and task.goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to access this task."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Serialize the task data
            task_serializer = TaskSerializer(task)
            return Response(task_serializer.data, status=status.HTTP_200_OK)

        except Task.DoesNotExist:
            raise Http404("Task not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetTasksByGoalIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            200: TaskSerializer(many=True),
            404: "Goal not found",
            401: "Unauthorized",
        },
        operation_description="Fetch all tasks for a goal by its ID"
    )
    def get(self, request, goal_id, *args, **kwargs):
        try:
            # Check if the goal exists and belongs to the authenticated user
            goal = Goal.objects.get(id=goal_id, user=request.user)

            # Fetch tasks related to the goal
            tasks = Task.objects.filter(goal=goal)

            # Serialize and return the tasks
            task_serializer = TaskSerializer(tasks, many=True)
            return Response(task_serializer.data, status=status.HTTP_200_OK)

        except Goal.DoesNotExist:
            raise Http404("Goal not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class GetAiTaskByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Goals"],
        responses={
            200: AiTaskSerializer,
            404: "Task not found",
            401: "Unauthorized",
        },
        operation_description="Fetch a task by its ID"
    )

    def get(self, request, task_id, *args, **kwargs):
        try:
            # Fetch the task by ID
            ai_task = AiTask.objects.get(id=task_id)

            # Check if the task belongs to the authenticated user
            if ai_task.ai_goal and ai_task.ai_goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to access this task."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Serialize the task data
            task_serializer = AiTaskSerializer(ai_task, context={"include_subtasks": True})
            return Response(task_serializer.data, status=status.HTTP_200_OK)

        except AiTask.DoesNotExist:
            raise Http404("Task not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class GetAiSubtaskByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Subtasks"],
        responses={
            200: AiSubTaskSerializer,
            404: "Subtask not found",
            403: "Forbidden - You do not own this subtask",
            500: "Internal Server Error",
        },
        operation_description="Fetch a subtask by its ID"
    )
    def get(self, request, task_id, subtask_id, *args, **kwargs):
        try:
            # Fetch the subtask and related goal via ai_task
            ai_subtask = AiSubTask.objects.select_related('ai_task__ai_goal').get(
                id=subtask_id,
                ai_task_id=task_id
            )

            # Check ownership
            if ai_subtask.ai_task.ai_goal.user != request.user:
                raise PermissionDenied("You do not have permission to access this subtask.")

            # Serialize and return
            serializer = AiSubTaskSerializer(ai_subtask)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except AiSubTask.DoesNotExist:
            raise Http404("Subtask not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteGoalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Goals"],
        responses={
            204: "Goal deleted successfully",
            404: "Goal not found",
            403: "You do not have permission to delete this goal",
            401: "Unauthorized",
        },
        operation_description="Delete a goal by its ID",
    )
    def delete(self, request, goal_id, *args, **kwargs):
        try:
            # Fetch the goal by ID
            goal = Goal.objects.get(id=goal_id)

            # Check if the goal belongs to the authenticated user
            if goal.user != request.user:
                raise PermissionDenied("You do not have permission to delete this goal.")

            # Delete the goal
            goal.delete()
            return Response({"message": "Goal deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

        except Goal.DoesNotExist:
            raise NotFound(detail="Goal not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteAiGoalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        responses={
            204: "Goal deleted successfully",
            404: "Goal not found",
            403: "You do not have permission to delete this goal",
            401: "Unauthorized",
        },
        operation_description="Delete Ai goal by its ID",
    )
    def delete(self, request, goal_id, *args, **kwargs):
        try:
            # Fetch the goal by ID
            ai_goal = AiGoal.objects.get(id=goal_id)

            # Check if the goal belongs to the authenticated user
            if ai_goal.user != request.user:
                raise PermissionDenied("You do not have permission to delete this goal.")

            # Delete the goal
            ai_goal.delete()
            return Response({"message": "Goal deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

        except AiGoal.DoesNotExist:
            raise NotFound(detail="Goal not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            204: "Task successfully deleted",
            403: "Forbidden: Task does not belong to the user",
            404: "Task not found",
            401: "Unauthorized",
        },
        operation_description="Delete a task by its ID",
    )
    def delete(self, request, task_id, *args, **kwargs):
        try:
            # Fetch the task by ID
            task = Task.objects.get(id=task_id)

            # Check if the task belongs to the authenticated user
            if task.goal and task.goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to delete this task."},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Delete the task
            task.delete()
            return Response({"message": "Task successfully deleted."}, status=status.HTTP_204_NO_CONTENT)

        except Task.DoesNotExist:
            # Handle case where task does not exist
            raise Http404("Task not found.")

        except Exception as e:
            # Handle unexpected errors
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteAiTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        responses={
            204: "Task successfully deleted",
            403: "Forbidden: Task does not belong to the user",
            404: "Task not found",
            401: "Unauthorized",
        },
        operation_description="Delete Ai task by its ID",
    )
    def delete(self, request, task_id, *args, **kwargs):
        try:
            # Fetch the task by ID
            ai_task = AiTask.objects.get(id=task_id)

            # Check if the task belongs to the authenticated user
            if ai_task.ai_goal and ai_task.ai_goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to delete this task."},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Delete the task
            ai_task.delete()
            return Response({"message": "Task successfully deleted."}, status=status.HTTP_204_NO_CONTENT)

        except AiTask.DoesNotExist:
            # Handle case where task does not exist
            raise Http404("Task not found.")

        except Exception as e:
            # Handle unexpected errors
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class DeleteUserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["User"],
        responses={
            204: "User profile and related data successfully deleted",
            401: "Unauthorized",
            500: "Unexpected error",
        },
        operation_description="Delete the authenticated user's profile and all associated data (goals and tasks).",
    )
    def delete(self, request, *args, **kwargs):
        try:
            user = request.user

            # Delete the user and cascade delete all related data
            user.delete()

            return Response(
                {"message": "User profile and all associated data successfully deleted."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            return Response(
                {"error": "An error occurred while deleting the user profile", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class UserGoalsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Goals"],
        responses={
            200: "User goals fetched successfully",
            401: "Unauthorized",
            500: "Unexpected error",
        },
        operation_description="Fetch all goals of the authenticated user, including regular goals and AI goals",
    )
    def get(self, request):
        try:
            user = request.user

            # Fetch the user's regular goals
            goals = Goal.objects.filter(user=user)
            goal_serializer = GoalSerializer(goals, many=True)

            # Fetch the user's AI goals
            ai_goals = AiGoal.objects.filter(user=user)
            ai_goal_serializer = AiGoalSerializer(ai_goals, many=True)

            # Build the response
            response_data = {
                "goals": goal_serializer.data,
                "ai_goals": ai_goal_serializer.data,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching user goals: {str(e)}")
            return Response(
                {"error": "An error occurred while fetching the user goals", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class TriggerTaskRemindersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "task_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "due_date": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "reminder_time": openapi.Schema(type=openapi.TYPE_STRING, format="time"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Task reminders triggered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: "Forbidden",
            500: "Unexpected error",
        },
        operation_description="Manually trigger task reminders",
    )
    def post(self, request):
        task_id = request.data.get("task_id")
        due_date = request.data.get("due_date")
        reminder_time = request.data.get("reminder_time")

        if not task_id:
            return Response({"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = Task.objects.get(id=task_id, user=request.user)

            # Update due_date and reminder_time if provided
            if due_date is not None:
                task.due_date = due_date
            if reminder_time is not None:
                task.reminder_time = reminder_time
                task.reminder_sent = False 

            task.save()

            # Check if both are now set
            if not task.due_date or not task.reminder_time:
                return Response(
                    {"error": "Task must have both due_date and reminder_time to trigger reminders."},
                    status=status.HTTP_400_BAD_REQUEST
                )

         
            return Response({"message": "Task reminders triggered successfully"}, status=status.HTTP_200_OK)

        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)


class TriggerAiSubTaskRemindersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "subtask_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "due_date": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "reminder_time": openapi.Schema(type=openapi.TYPE_STRING, format="time"),
            },
        ),
        responses={
            200: openapi.Response(
                description="AI task reminders triggered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: "Forbidden",
            500: "Unexpected error",
        },
        operation_description="Manually trigger AI subtask reminders",
    )


    def post(self, request):
        subtask_id = request.data.get("subtask_id")
        due_date = request.data.get("due_date")
        reminder_time = request.data.get("reminder_time")



        if not subtask_id:
            return Response({"error": "subtask_id is required"}, status=status.HTTP_400_BAD_REQUEST)

       

        try:
            ai_subtask = AiSubTask.objects.get(id=subtask_id, ai_task__ai_goal__user=request.user)


            # Update due_date and reminder_time if provided
            if due_date is not None:
                ai_subtask.due_date = due_date
            if reminder_time is not None:
                ai_subtask.reminder_time = reminder_time
                ai_subtask.reminder_sent = False 

            ai_subtask.save()

            # Check if both are now set
            if not ai_subtask.due_date or not ai_subtask.reminder_time:
                return Response(
                    {"error": "Ai Task must have both due_date and reminder_time to trigger reminders."},
                    status=status.HTTP_400_BAD_REQUEST
                )

         
            return Response({"message": "Ai subtask reminders triggered successfully"}, status=status.HTTP_200_OK)

        except AiSubTask.DoesNotExist:
            return Response({"error": " Ai subtask not found"}, status=status.HTTP_404_NOT_FOUND)



class TriggerAiTaskRemindersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "task_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "due_date": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "reminder_time": openapi.Schema(type=openapi.TYPE_STRING, format="time"),
            },
        ),
        responses={
            200: openapi.Response(
                description="AI task reminders triggered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: "Forbidden",
            500: "Unexpected error",
        },
        operation_description="Manually trigger AI task reminders",
    )


    def post(self, request):
        task_id = request.data.get("task_id")
        due_date = request.data.get("due_date")
        reminder_time = request.data.get("reminder_time")



        if not task_id:
            return Response({"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST)

       

        try:
            ai_task = AiTask.objects.get(id=task_id, ai_goal__user=request.user)


            # Update due_date and reminder_time if provided
            if due_date is not None:
                ai_task.due_date = due_date
            if reminder_time is not None:
                ai_task.reminder_time = reminder_time
                ai_task.reminder_sent = False 

            ai_task.save()

            # Check if both are now set
            if not ai_task.due_date or not ai_task.reminder_time:
                return Response(
                    {"error": "Ai Task must have both due_date and reminder_time to trigger reminders."},
                    status=status.HTTP_400_BAD_REQUEST
                )

         
            return Response({"message": "Ai task reminders triggered successfully"}, status=status.HTTP_200_OK)

        except AiTask.DoesNotExist:
            return Response({"error": " Ai task not found"}, status=status.HTTP_404_NOT_FOUND)



class GetAllUserTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            200: TaskSerializer(many=True),
            403: "Forbidden",
            500: "Unexpected error",
        },
        operation_description="Get all tasks for the authenticated user",
    )
    def get(self, request):
        user = request.user
        logger.debug(f"Fetching tasks for user: {user.email}")
        tasks = Task.objects.filter(user=user)
        logger.debug(f"Found {tasks.count()} tasks for user: {user.email}")
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DeleteAllUserTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            204: "No Content",
            403: "Forbidden",
            500: "Unexpected error",
        },
        operation_description="Delete all tasks for the authenticated user",
    )
    def delete(self, request):
        user = request.user
        tasks_deleted, _ = Task.objects.filter(user=user).delete()
        logger.info(f"Deleted {tasks_deleted} tasks for user: {user.email}")
        return Response(status=status.HTTP_204_NO_CONTENT)

class CreateAiTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=CreateAiTaskSerializer,
        responses={
            201: AiTaskSerializer,
            400: "Validation error",
            404: "Goal Not Found",
            500: "Unexpected error",
        },
        operation_description="Create a new AI Task under an AI Goal",
    )

    def post(self, request, *args, **kwargs):
        goal_id = kwargs.get("id")

        if not goal_id:
            return Response({"error": "Goal ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ai_goal = AiGoal.objects.get(id=goal_id, user=request.user)
        except AiGoal.DoesNotExist:
            return Response(
                {"error": f"AI Goal with ID {goal_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data["goal"] = ai_goal.id  # Associate task with goal
        serializer = CreateAiTaskSerializer(data=data)

        if serializer.is_valid():
            ai_task = serializer.save()
            return Response(AiTaskSerializer(ai_task).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CreateSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        request_body=SubTaskSerializer,
        responses={
            201: SubTaskSerializer,
            400: "Validation error",
            404: "Task not found",
            500: "Unexpected error",
        },
        operation_description="Create a new subtask for a task",
    )
    def post(self, request, *args, **kwargs):
        task_id = kwargs.get("task_id")

        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response(
                {"error": f"Task with ID {task_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data["task"] = task.id  # Associate subtask with task
        serializer = SubTaskSerializer(data=data)

        if serializer.is_valid():
            subtask = serializer.save()
            return Response(SubTaskSerializer(subtask).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateAiSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Ai Tasks"],
        request_body=AiSubTaskSerializer,
        responses={
            201: AiSubTaskSerializer,
            400: "Validation error",
            404: "AI Task not found",
            500: "Unexpected error",
        },
        operation_description="Create an AI subtask for a given AI task",
    )
    def post(self, request, task_id, *args, **kwargs): 
        try:
            ai_task = AiTask.objects.get(id=task_id, ai_goal__user=request.user)
        except AiTask.DoesNotExist:
            return Response({"error": "AI Task not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["ai_task"] = ai_task.id  # Assign the AiTask to the subtask

        serializer = AiSubTaskSerializer(data=data, context={"ai_task_id": ai_task.id} )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateAiSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Ai Tasks"],
        request_body=AiSubTaskSerializer,
        responses={
            200: AiSubTaskSerializer,
            400: "Validation error",
            404: "Task or Subtask not found",
            500: "Unexpected error",
        },
        operation_description="Update an AI subtask within a specific AI task",
    )
    def patch(self, request, *args, **kwargs):
        task_id = kwargs.get("task_id")  # Extract AiTask ID from URL
        subtask_id = kwargs.get("subtask_id")  # Extract AiSubTask ID from URL

        try:
            # Ensure the AiTask belongs to the authenticated user
            task = AiTask.objects.get(id=task_id, ai_goal__user=request.user)
        except AiTask.DoesNotExist:
            return Response({"error": "AI Task not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Ensure the AiSubTask belongs to the given AiTask
            subtask = AiSubTask.objects.get(id=subtask_id, ai_task=task)
        except AiSubTask.DoesNotExist:
            return Response({"error": "AI Subtask not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AiSubTaskSerializer(subtask, data=request.data, partial=True)  # Allow partial updates
        if serializer.is_valid():
            serializer.save()

            log_activity(
                user=request.user,
                activity_type="ai_subtask_updated",
                metadata={
                    "subtask_id": updated_subtask.id,
                    "updated_fields": list(request.data.keys()),
                    "task_id": task.id,
                    "goal_id": task.ai_goal.id if hasattr(task, "ai_goal") else None,
                    "tags": list(
                        filter(
                            None,
                            [task.ai_goal.tag if task.ai_goal else None]
                        )
                    )
                }
            )


            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        request_body=SubTaskSerializer,
        responses={
            200: SubTaskSerializer,
            400: "Validation error",
            404: "Task or Subtask not found",
            500: "Unexpected error",
        },
        operation_description="Update an AI subtask within a specific AI task",
    )
    def patch(self, request, *args, **kwargs):
        task_id = kwargs.get("task_id")  # Extract AiTask ID from URL
        subtask_id = kwargs.get("subtask_id")  # Extract AiSubTask ID from URL

        try:
            # Ensure the AiTask belongs to the authenticated user
            task = Task.objects.filter(id=task_id, user=request.user).first()  # Updated filter query
            if not task:
                return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Ensure the AiSubTask belongs to the given AiTask
            subtask = SubTask.objects.get(id=subtask_id, task=task)
        except SubTask.DoesNotExist:
            return Response({"error": "Subtask not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubTaskSerializer(subtask, data=request.data, partial=True)  # Allow partial updates
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        operation_description="Delete a subtask by ID",
        responses={
            204: "Subtask deleted successfully",
            404: "Subtask not found",
            403: "Forbidden",
        }
    )
    def delete(self, request, subtask_id, *args, **kwargs):
        try:
            subtask = SubTask.objects.get(id=subtask_id, task__user=request.user)
        except SubTask.DoesNotExist:
            return Response({"error": "Subtask not found."}, status=status.HTTP_404_NOT_FOUND)

        subtask.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeleteAiSubtaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Ai Tasks"],
        operation_description="Delete an AI subtask by ID",
        responses={
            204: "AI Subtask deleted successfully",
            404: "AI Subtask not found",
            403: "Forbidden",
        }
    )
    def delete(self, request, ai_subtask_id, *args, **kwargs):
        try:
            ai_subtask = AiSubTask.objects.get(id=ai_subtask_id, ai_task__ai_goal__user=request.user)
        except AiSubTask.DoesNotExist:
            return Response({"error": "AI Subtask not found."}, status=status.HTTP_404_NOT_FOUND)

        ai_subtask.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




class AnswerAiSubtaskQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Ai Tasks"],
        responses={
            200: openapi.Response(
                description="Answer to the subtask question",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "answer": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: "Subtask not found",
            401: "Unauthorized",
        },
        operation_description="Generate and store an AI answer for a specific AiSubTask",
    )
    def post(self, request, subtask_id):
        try:
            subtask = AiSubTask.objects.get(id=subtask_id, ai_task__ai_goal__user=request.user)
        except AiSubTask.DoesNotExist:
            return Response({"error": "Subtask not found"}, status=404)

        # ✅ Call the new version of your function
        answer = answer_subtask_question(subtask)

        subtask.ai_answer = answer
        subtask.save(update_fields=["ai_answer"])

        return Response({"answer": answer}, status=200)


class AnswerTaskQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["Tasks"],
        responses={
            200: openapi.Response(
                description="Answer to the task question",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "answer": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: "Task not found",
            401: "Unauthorized",
        },
        operation_description="Generate and store an AI answer for a specific Task",
    )
    def post(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)

        # ✅ Call the correct helper
        answer = answer_task_question(task)

        task.ai_answer = answer
        task.save(update_fields=["ai_answer"])

        return Response({"answer": answer}, status=200)






class RoutineListCreateView(generics.ListCreateAPIView):
    serializer_class = RoutineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        today = timezone.now().date()
        return Routine.objects.filter(
            user=self.request.user,
            is_active=True
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Get all routines for the authenticated user",
        tags=["Routines"],
        responses={200: RoutineSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new routine",
        tags=["Routines"],
        request_body=RoutineSerializer,
        responses={201: RoutineSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)




class RoutineDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoutineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Routine.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a specific routine by ID",
        tags=["Routines"],
        responses={200: RoutineSerializer, 404: "Not Found"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a routine by ID (partial updates supported)",
        tags=["Routines"],
        request_body=RoutineSerializer,
        responses={200: RoutineSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a routine by ID",
        tags=["Routines"],
        responses={204: "Deleted successfully", 404: "Not Found"}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)



class TemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        
        serializer.save(user=self.request.user)
        

    @swagger_auto_schema(
        operation_description="Get all daily templates for the authenticated user",
        tags=["Daily Templates"],
        responses={200: TemplateSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new daily template (first one includes default template suggestion)",
        tags=["Daily Templates"],
        request_body=TemplateSerializer,
        responses={201: TemplateSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a specific daily template by ID",
        tags=["Daily Templates"],
        responses={200: TemplateSerializer, 404: "Not Found"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a daily template by ID (partial updates supported)",
        tags=["Daily Templates"],
        request_body=TemplateSerializer,
        responses={200: TemplateSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a daily template by ID",
        tags=["Daily Templates"],
        responses={204: "Deleted successfully", 404: "Not Found"}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class DailyActivityListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        view_type = self.request.query_params.get("view", "today")
        if view_type == "history":
            return DailyActivityHistorySerializer
        return DailyActivitySerializer

    def get_queryset(self):
        user = self.request.user
        view_type = self.request.query_params.get("view", "today")
        now_utc = timezone.now()
       
        # ✅ Convert UTC → user’s local timezone
        try:
            user_tz = pytz.timezone(user.timezone)
        except Exception:
            user_tz = pytz.UTC

        user_local_today = now_utc.astimezone(user_tz).date()

        if view_type == "history":
            return DailyActivityHistory.objects.filter(
                activity__template__user=user
            ).order_by("-date")

        # ✅ Use user-local "today"
        return DailyActivity.objects.filter(
            template__user=user,
            date=user_local_today
        ).order_by("start_time")

    def perform_create(self, serializer):
        template_id = self.request.data.get("template")
        serializer.save(template_id=template_id)

    @swagger_auto_schema(
        operation_description="Get daily activities (default: today). Use ?view=history to see past activities.",
        tags=["Daily Activities"],
        responses={200: DailyActivitySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new daily activity under a specific template",
        tags=["Daily Activities"],
        request_body=DailyActivitySerializer,
        responses={201: DailyActivitySerializer, 400: "Bad Request"}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DailyActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DailyActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DailyActivity.objects.filter(template__user=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a specific daily activity by ID",
        tags=["Daily Activities"],
        responses={200: DailyActivitySerializer, 404: "Not Found"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a daily activity by ID (partial updates supported)",
        tags=["Daily Activities"],
        request_body=DailyActivitySerializer,
        responses={200: DailyActivitySerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a daily activity by ID (fixed activities cannot be deleted)",
        tags=["Daily Activities"],
        responses={204: "Deleted successfully", 400: "Cannot delete fixed activity", 404: "Not Found"}
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_fixed:
            raise ValidationError({"detail": "Fixed activities cannot be deleted."})
        return super().delete(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """Extra safeguard: block deletion of fixed activities."""
        if instance.is_fixed:
            raise ValidationError({"detail": "Fixed activities cannot be deleted."})
        instance.delete()

class DailyActivityCompleteView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Mark a daily activity as complete or incomplete.",
        tags=["Daily Activities"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "completed": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Set to true to mark as completed, false to mark as incomplete."
                ),
            },
            required=["completed"],
        ),
        responses={
            200: "Activity status updated successfully",
            404: "Activity not found",
        },
    )
    def patch(self, request, pk):
        try:
            activity = DailyActivity.objects.get(pk=pk, template__user=request.user)
        except DailyActivity.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        activity.completed = request.data.get("completed", True)
        activity.save(update_fields=["completed"])
        return Response(
            {"id": activity.id, "completed": activity.completed},
            status=status.HTTP_200_OK,
        )

class SuggestedTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get suggested daily templates",
        operation_description="Retrieve a list of default suggested templates that users can save or customize.",
        responses={
            200: openapi.Response(
                description="List of suggested templates",
                examples={
                    "application/json": [
                        {
                            "name": "🌞 Daily Planning Template",
                            "description": "A balanced plan for your day with built-in activities",
                            "activities": FIXED_ACTIVITIES,
                        }
                    ]
                },
            )
        },
    )
    def get(self, request):
        """Return the default suggested templates (only those not already saved by the user)."""
        user = request.user

        # All possible suggestions
        suggestions = [
            {
                "name": "🌞 Daily Planning Template",
                "description": "A balanced plan for your day with built-in activities",
                "activities": FIXED_ACTIVITIES,
            }
        ]

        # Get names of templates the user already has
        existing_names = set(
            Template.objects.filter(user=user).values_list("name", flat=True)
        )

        # Only show suggestions not already saved
        filtered_suggestions = [
            s for s in suggestions if s["name"] not in existing_names
        ]

        return Response(filtered_suggestions)


class SaveSuggestedTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Save a suggested template",
        operation_description="Save a suggested daily template (with fixed activities) to the user's account.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "activities"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="Template name"),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Template description"),
                "activities": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="List of activities in the template",
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "title": openapi.Schema(type=openapi.TYPE_STRING),
                            "start_time": openapi.Schema(type=openapi.TYPE_STRING, example="08:00"),
                            "end_time": openapi.Schema(type=openapi.TYPE_STRING, example="09:00"),
                        },
                    ),
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Template created successfully",
                schema=TemplateSerializer,
            ),
        },
    )
    def post(self, request):
        user = request.user
        name = request.data.get("name")
        description = request.data.get("description", "")
        activities = request.data.get("activities", [])

        template = Template.objects.create(
            user=user,
            name=name,
            description=description,
            is_active=True,
        )

        for activity in activities:
            DailyActivity.objects.create(
                template=template,
                title=activity["title"],
                start_time=activity["start_time"],
                end_time=activity.get("end_time"),
                is_fixed=True,
            )

        serializer = TemplateSerializer(template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

