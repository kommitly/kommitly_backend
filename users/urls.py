from django .urls import path
from .views import CreateUserView, LoginUserView, VerifyUserView, VerifyEmailChangeView, CheckVerificationStatusView, GetUserView, UpdateAuthenticatedUserView, UpdateUserByEmailView, DeleteAuthenticatedUserView, DeleteUserByEmailView, GetTimezoneView, GoogleAuthView, DashboardStatsView, PasswordResetRequestView, PasswordResetConfirmView, PasswordChangeView


urlpatterns = [
    path("users/signup", CreateUserView.as_view(), name="user_signup"),
    path("verify/<str:token>/", VerifyUserView.as_view(), name="verify_user"),
    path('verify-email/<str:token>/', VerifyEmailChangeView.as_view(), name='verify-email-change'),
    path("users/get-user/<str:email>/", GetUserView.as_view(), name="get_user_details"),
    path("users/user/update/", UpdateAuthenticatedUserView.as_view(), name="update_user_details"),
    path("users/user/update-by-email/<str:email>/", UpdateUserByEmailView.as_view(), name="update_user_by_email"),
    path("users/user/delete/", DeleteAuthenticatedUserView.as_view(), name="delete_user"),
    path("users/user/delete-by-email/<str:email>/", DeleteUserByEmailView.as_view(), name="delete_user_by_email"),
    path("users/check-verification-status/<str:email>/", CheckVerificationStatusView.as_view(), name="check-verification"),
    path("users/login", LoginUserView.as_view(), name="login"),
    path('users/get-timezone/', GetTimezoneView.as_view(), name='get-timezone'),
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
    path("users/stats/", DashboardStatsView.as_view(), name='dashboard-stats'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),
]


    

