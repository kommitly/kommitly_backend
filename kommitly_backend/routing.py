from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/verify/<str:token>/", consumers.VerificationConsumer.as_asgi()),
]