from django.urls import path
from .views import NotificationListView, SingleTaskNotificationView, MarkNotificationAsReadView, MarkAllNotificationsAsReadView


urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/task/<int:task_id>/', SingleTaskNotificationView.as_view(), name='task-notification-detail'),
    path('notifications/<int:notification_id>/mark-read/', MarkNotificationAsReadView.as_view(), name='mark-notification-as-read'),
    path('notifications/mark-all-read/', MarkAllNotificationsAsReadView.as_view(), name='mark_all_notifications_read'),
]
