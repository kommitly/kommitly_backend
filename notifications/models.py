
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from goals.models import Task  # existing

class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    
    # Legacy field for Task (keep this for old data)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)

    # New polymorphic fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    message = models.TextField()
    link = models.URLField(null=True, blank=True)
    type = models.CharField(max_length=50, default='reminder')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} for {self.user.first_name}: {self.message[:30]}"