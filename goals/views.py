import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Goal, Task, AiGoal, AiTask
from .serializers import GoalSerializer, TaskSerializer, CreateGoalSerializer, CreateTaskSerializer, AiGoalSerializer, AiTaskSerializer, CreateAiGoalSerializer, UserProfileSerializer, UpdateAiGoalSerializer
import kommitly_backend.settings as st
from drf_yasg.utils import swagger_auto_schema
from django.core.exceptions import ValidationError
from ai_insights.utils import get_insights
from drf_yasg import openapi
from users.models import User
from django.http import Http404

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
                                    'actionable_steps': openapi.Schema(type=openapi.TYPE_STRING),
                                    'task_timeline': openapi.Schema(type=openapi.TYPE_STRING),
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
                insights = get_insights(goal_data['title'])

                # Print the insights for debugging
                print("Goal Title:", goal_data['title'])
                print("Insights:", insights)

                if not insights:
                    return Response({"error": "No insights returned from AI service."}, status=status.HTTP_400_BAD_REQUEST)

                # Generate tasks from insights
                ai_tasks = []
                for step in insights:
                    task_data = {
                        "title": step.get("task_title"),
                        "due_date": None,  # Handle missing due_date
                        "status": "pending",
                        "actionable_steps": step.get("actionable_steps"),  # Include actionable steps
                        "task_timeline": step.get("task_timeline")  # Include task timeline
                    }
                    ai_tasks.append(task_data)

                # Prepare response data
                response_data = {
                    "ai_goal": {
                        "title": goal_data['title'],
                        "description": goal_data['description'],
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
                            'actionable_steps': openapi.Schema(type=openapi.TYPE_STRING),
                            'task_timeline': openapi.Schema(type=openapi.TYPE_STRING),
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
                for task_data in ai_tasks_data:
                    task_data['ai_goal'] = ai_goal.id
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
                return Response({"error": f"An error occurred while saving tasks: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
        serializer = CreateGoalSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            goal = serializer.save()
            return Response(GoalSerializer(goal).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



        serialize
        
 
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
        serializer = CreateTaskSerializer(data=request.data)
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
            tasks = Task.objects.filter(goal__user=user) | Task.objects.filter(goal__isnull=True)
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
        
        # Check if the user exists
        try:
            user = User.objects.get(id=user.id)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)


        task_id = kwargs.get("id")  # Extract task ID from URL
        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Fetch the task that belongs to the authenticated user
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"error": "Task not found or does not belong to the user."}, status=status.HTTP_404_NOT_FOUND)
        
        # Update task using serializer
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            updated_task = serializer.save()
            return Response(TaskSerializer(updated_task).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateAuthenticatedAiTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=["AI Goals"],
        request_body=AiTaskSerializer,
        responses={
            200: AiTaskSerializer,
            400: "Validation error",
            404: "Task not found",
            500: "Unexpected error",
        },
        operation_description="Update Ai task for the authenticated user",
    )
    def patch(self, request, *args, **kwargs):
        
        # Check if the user exists
        try:
            user = User.objects.get(id=user.id)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)


        task_id = kwargs.get("id")  # Extract task ID from URL
        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Fetch the task that belongs to the authenticated user
            ai_task = AiTask.objects.get(id=task_id, user=request.user)
        except AiTask.DoesNotExist:
            return Response({"error": "Task not found or does not belong to the user."}, status=status.HTTP_404_NOT_FOUND)
        
        # Update task using serializer
        serializer = AiTaskSerializer(ai_task, data=request.data, partial=True)
        if serializer.is_valid():
            updated_task = serializer.save()
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
            # Fetch the goal by ID
            ai_goal = AiGoal.objects.get(id=goal_id)

            # Check if the goal belongs to the authenticated user
            if ai_goal.user != request.user:
                return Response(
                    {"error": "You do not have permission to access this goal."},
                    status=status.HTTP_403_FORBIDDEN
                )

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
            task_serializer = AiTaskSerializer(ai_task)
            return Response(task_serializer.data, status=status.HTTP_200_OK)

        except AiTask.DoesNotExist:
            raise Http404("Task not found.")

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

