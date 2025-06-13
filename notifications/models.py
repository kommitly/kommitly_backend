
from django.db import models
from django.contrib.auth import get_user_model
from goals.models import Task


class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications') 
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    link = models.URLField(null=True, blank=True)
    type = models.CharField(max_length=50, default='reminder')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} for {self.user.first_name}: {self.message[:30]}"
