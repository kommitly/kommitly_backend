from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from timezonefinder import TimezoneFinder

def get_timezone(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            tf = TimezoneFinder()
            timezone = tf.timezone_at(lat=latitude, lng=longitude)

            if timezone:
                return JsonResponse({'timezone': timezone}, status=200)
            else:
                return JsonResponse({'error': 'Could not determine timezone'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
