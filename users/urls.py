from django .urls import path
from .views import CreateUserView

urlpatterns = [
    path("users/signup", CreateUserView.as_view(), name="user_signup"),
]