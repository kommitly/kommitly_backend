from rest_framework import serializers
from .models import AIInsight

class AIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsight
        fields = [
            'id', 
            'goal', 
            'insight_text', 
            'created_at', 
            'updated_at'
            ]
