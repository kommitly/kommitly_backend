
from django.db import models
from django.contrib.auth import get_user_model
from goals.models import Task

User = get_user_model()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    type = models.CharField(max_length=50, default='reminder')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} for {self.user.username}: {self.message}"
