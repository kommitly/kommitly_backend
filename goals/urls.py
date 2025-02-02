from django .urls import path
from .views import (
    CreateGoalView, 
    CreateTaskView, 
    CreateGoalWithAIInsightsView, 
    UpdateGoalByEmailView, 
    UpdateAuthenticatedGoalView, 
    UserAuthenticatedProfileView, 
    UpdateAuthenticatedTaskView, 
    GetGoalByIdView, 
    GetTaskByIdView, 
    DeleteGoalView, 
    DeleteTaskView,
    DeleteUserProfileView,
    UpdateAuthenticatedAiGoalView,
    UpdateAuthenticatedAiTaskView,
    DeleteAiTaskView,
    DeleteAiGoalView,
    GetAiGoalByIdView,
    GetAiTaskByIdView,
    GenerateAIInsightsView,
)


urlpatterns= [
    path('goals/create/goal/', CreateGoalView.as_view(), name='create_goal'),
    path('goals/create/task/', CreateTaskView.as_view(), name='create_task'),
    path('goals/create-goal-ai/', CreateGoalWithAIInsightsView.as_view(), name='create_goal_with_ai'),
    path('goals/generate-ai-insights/', GenerateAIInsightsView.as_view(), name='generate_ai_insights'),  # Add this URL pattern
    path('goals/update-goal/<str:email>/<int:id>/', UpdateGoalByEmailView.as_view(), name='update_goal_by_email'),
    path('goals/<int:id>/update/', UpdateAuthenticatedGoalView.as_view(), name='update_authenticated_goal'),
    path('users/profile/', UserAuthenticatedProfileView.as_view(), name='user_profile'),
    path('tasks/<int:id>/update/', UpdateAuthenticatedTaskView.as_view(), name='update_authenticated_task'),
    path('goals/<int:goal_id>/', GetGoalByIdView.as_view(), name='get_goal_by_id'),
    path('tasks/<int:task_id>/', GetTaskByIdView.as_view(), name='get_task_by_id'),
    path('goals/<int:goal_id>/delete/', DeleteGoalView.as_view(), name='delete_goal'),
    path('tasks/<int:task_id>/delete/', DeleteTaskView.as_view(), name='delete_task'),
    path('users/delete-profile/', DeleteUserProfileView.as_view(), name='delete_user_profile'),
    path('goals/<int:id>/update-ai-goal/', UpdateAuthenticatedAiGoalView.as_view(), name='update_authenticated_ai_goal'),
    path('tasks/<int:task_id>/update-ai-task/', UpdateAuthenticatedAiTaskView.as_view(), name='update_authenticated_ai_task'),
    path('goals/<int:goal_id>/delete-ai-goal/', DeleteAiGoalView.as_view(), name='delete_ai_goal'),
    path('tasks/<int:task_id>/delete-ai-task/', DeleteAiTaskView.as_view(), name='delete_ai_task'),
    path('goals/<int:goal_id>/ai-goal/', GetAiGoalByIdView.as_view(), name='get_ai_goal_by_id'),
    path('tasks/<int:task_id>/ai-task/', GetAiTaskByIdView.as_view(), name='get_ai_task_by_id'),
    
    
    
    

]