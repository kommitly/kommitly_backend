from django.urls import path
from .views import NotificationListView, SingleTaskNotificationView, MarkNotificationAsReadView


urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/task/<int:task_id>/', SingleTaskNotificationView.as_view(), name='task-notification-detail'),
    path('notifications/<int:notification_id>/mark-read/', MarkNotificationAsReadView.as_view(), name='mark-notification-as-read'),
]
