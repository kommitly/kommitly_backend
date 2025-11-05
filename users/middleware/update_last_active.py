from django.utils import timezone
from datetime import timedelta

class UpdateLastActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            now = timezone.now()
            last_active = request.user.last_active

            # Only update if user hasn't been active in the last 5 minutes
            if not last_active or (now - last_active) > timedelta(minutes=5):
                request.user.last_active = now
                request.user.save(update_fields=["last_active"])

        return response
