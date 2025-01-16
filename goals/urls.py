from django .urls import path
from .views import CreateGoalView, CreateTaskView, CreateGoalWithAIInsightsView

urlpatterns= [
    path('create/goal/', CreateGoalView.as_view(), name='create_goal'),
    path('create/task/', CreateTaskView.as_view(), name='create_task'),
    path('create-goal-ai/', CreateGoalWithAIInsightsView.as_view(), name='create_goal_with_ai'),
    

]