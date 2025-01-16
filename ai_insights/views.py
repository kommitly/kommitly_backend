from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import get_insights  # Assuming the function is in utils.py or appropriate module

@csrf_exempt
def get_goal_insights(request):
    if request.method == "POST":
        try:
            # Assuming the goal is sent in the POST body as JSON
            goal = request.POST.get('goal')
            
            if not goal:
                return JsonResponse({"error": "Goal is required"}, status=400)

            insights = get_insights(goal)
            return JsonResponse({"insights": insights}, status=200)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid HTTP method"}, status=405)
