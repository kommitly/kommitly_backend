# Assuming this middleware file is in an app where UserActivity is accessible,
# or you adjust the import path.
from django.utils import timezone
from datetime import timedelta
# Add this import line:
from users.models import UserActivity 
from users.utils import log_activity

class UpdateLastActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            now = timezone.now()
            last_active = request.user.last_active

            # Check if user hasn't been active in the last 5 minutes
            if not last_active or (now - last_active) > timedelta(minutes=5):
                
                # 1. UPDATE last_active FIELD (Existing Logic)
                request.user.last_active = now
                request.user.save(update_fields=["last_active"])
                
                # 2. CREATE A NEW ACTIVITY LOG (New Logic)
                log_activity(
                    request.user,
                    "active_session",
                    {"path": request.path}
                )
                print(f"--- LOGGED NEW ACTIVITY for {request.user.email} ---") # Optional check/debug print

        return response