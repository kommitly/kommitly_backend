from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/verify/(?P<token>[^/]+)/$", consumers.VerificationConsumer.as_asgi()),
]
