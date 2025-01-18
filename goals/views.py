import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Goal, Task
from .serializers import GoalSerializer, TaskSerializer, CreateGoalSerializer, CreateTaskSerializer
import kommitly_backend.settings as st
from drf_yasg.utils import swagger_auto_schema
from django.core.exceptions import ValidationError
from ai_insights.utils import get_insights
from drf_yasg import openapi

# Create your views here.
class CreateGoalWithAIInsightsView(APIView):
    permission_classes = [permissions.AllowAny]  # Ensure user is authenticated

    @swagger_auto_schema(
        tags=["Goals"],
        request_body=CreateGoalSerializer,
        responses={
            201: openapi.Response(
                description="Goal created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "goal": openapi.Schema(
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
                        "tasks": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'goal': openapi.Schema(type=openapi.TYPE_INTEGER),
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
        # Deserialize the goal data
        goal_serializer = CreateGoalSerializer(data=request.data, context={"request": request})
        
        if goal_serializer.is_valid():
            # Save the goal to the database
            goal = goal_serializer.save()

            try:
                # Call AI insights utility to get actionable steps
                insights = get_insights(goal.title)

                # Print the insights for debugging
                print("Goal Title:", goal.title)
                print("Insights:", insights)

                if not insights:
                    return Response({"error": "No insights returned from AI service."}, status=status.HTTP_400_BAD_REQUEST)

                # Generate tasks from insights
                tasks = []
                for step in insights:
                    task_data = {
                        "goal": goal.id,
                        "title": step.get("task_title"),
                        "due_date": None,  # Handle missing due_date
                        "status": "pending",
                        "actionable_steps": step.get("actionable_steps"),  # Include actionable steps
                        "task_timeline": step.get("task_timeline")  # Include task timeline
                    }
                    task_serializer = TaskSerializer(data=task_data)
        
                    if task_serializer.is_valid():
                        task = task_serializer.save()
                        tasks.append(task)
                    else:
                        return Response(task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # Prepare response data
                response_data = {
                    "goal": GoalSerializer(goal).data,
                    "tasks": TaskSerializer(tasks, many=True).data,
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": f"An error occurred while generating insights: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(goal_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateGoalView(APIView):

    permission_classes = [permissions.AllowAny]

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



        
        
 
class CreateTaskView(APIView):
    permission_classes = [permissions.AllowAny]

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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)