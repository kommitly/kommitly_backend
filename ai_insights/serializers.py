from rest_framework import serializers
from .models import AIInsight

class AIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsight
        fields = [
            'id', 
            'ai_goal', 
            'insight_text', 
            'created_at', 
            'updated_at'
            ]
