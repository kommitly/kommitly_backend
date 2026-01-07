from users.models import UserActivity

def log_activity(user, activity_type, metadata=None):
    if not user or not user.is_authenticated:
        return
    
    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        metadata=metadata or {}
    )

