from django.shortcuts import render
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

# Create your views here.
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve notifications for the current user, optionally filtered by task ID.",
        tags=["Notifications"],
        manual_parameters=[
            openapi.Parameter(
                'task_id', openapi.IN_QUERY, description="Filter notifications by Task ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response(
                description="List of notifications",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "message": openapi.Schema(type=openapi.TYPE_STRING),
                            "link": openapi.Schema(type=openapi.TYPE_STRING, format="uri"),
                            "type": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_read": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        },
                    )
                )
            ),
            401: "Unauthorized"
        }
    )
    def get(self, request):
        task_id = request.query_params.get("task_id")
        notifications = Notification.objects.filter(user=request.user)

        if task_id:
            notifications = notifications.filter(task_id=task_id)

        data = NotificationSerializer(notifications.order_by('-created_at'), many=True).data
        return Response(data, status=status.HTTP_200_OK)