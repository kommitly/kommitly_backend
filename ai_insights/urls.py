from django .urls import path
from . import views

urlpatterns = [
    path('get-insights/', views.get_goal_insights, name='get_goal_insights'),
    
]