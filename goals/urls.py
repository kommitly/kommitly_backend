from django .urls import path
from .views import CreateGoalView, CreateTaskView, CreateGoalWithAIInsightsView, UpdateGoalByEmailView, UpdateAuthenticatedGoalView, UserAuthenticatedProfileView, UpdateAuthenticatedTaskView, GetGoalByIdView

urlpatterns= [
    path('goals/create/goal/', CreateGoalView.as_view(), name='create_goal'),
    path('goals/create/task/', CreateTaskView.as_view(), name='create_task'),
    path('goals/create-goal-ai/', CreateGoalWithAIInsightsView.as_view(), name='create_goal_with_ai'),
    path('goals/update-goal/<str:email>/<int:id>/', UpdateGoalByEmailView.as_view(), name='update_goal_by_email'),
    path('goals/<int:id>/update/', UpdateAuthenticatedGoalView.as_view(), name='update_authenticated_goal'),
    path('users/profile/', UserAuthenticatedProfileView.as_view(), name='user_profile'),
    path('tasks/<int:id>/update/', UpdateAuthenticatedTaskView.as_view(), name='update_authenticated_task'),
    path('goals/<int:goal_id>/', GetGoalByIdView.as_view(), name='get_goal_by_id'),

    

]