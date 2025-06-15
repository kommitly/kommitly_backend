from rest_framework import serializers
from .models import Notification
from django.contrib.contenttypes.models import ContentType

class NotificationSerializer(serializers.ModelSerializer):
    content_object = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'message',
            'task',  # legacy support
            'link',
            'type',
            'is_read',
            'created_at',
            'content_object',  # polymorphic reference
        ]

    def get_content_object(self, obj):
        if obj.content_object:
            return {
                'id': obj.object_id,
                'type': obj.content_type.model,  # e.g. "aitask" or "aisubtask"
                'repr': str(obj.content_object)
            }
        return None
