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
    operation_description="Retrieve notifications for the current user, optionally filtered by related content.",
    tags=["Notifications"],
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
                        "content_type": openapi.Schema(type=openapi.TYPE_STRING, description="Model name of related object"),
                        "object_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of related object"),
                    },
                )
            )
        ),
        401: "Unauthorized"
    }
)
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        data = NotificationSerializer(notifications, many=True).data
        return Response(data, status=status.HTTP_200_OK)



class SingleTaskNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get the latest notification for a specific task.",
        tags=["Notifications"],
        
     
        responses={
            200: openapi.Response(
                description="Notification for the task",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                   properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "link": openapi.Schema(type=openapi.TYPE_STRING, format="uri"),
                        "type": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_read": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "content_type": openapi.Schema(type=openapi.TYPE_STRING, description="Model name of related object"),
                        "object_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of related object"),
                    },
                )
            ),
            404: "Notification not found",
            401: "Unauthorized"
        }
    )
    def get(self, request, task_id):
        notification = Notification.objects.filter(user=request.user, task_id=task_id).order_by('-created_at').first()

        if not notification:
            return Response({"detail": "Notification not found for this task."}, status=status.HTTP_404_NOT_FOUND)

        data = NotificationSerializer(notification).data
        return Response(data, status=status.HTTP_200_OK)


class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Mark a specific notification as read.",
        tags=["Notifications"],
        responses={204: "Marked as read", 404: "Not found", 401: "Unauthorized"}
    )
    def patch(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
