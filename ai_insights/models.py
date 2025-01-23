from django.db import models

# Create your models here.

class AIInsight(models.Model):
    ai_goal = models.ForeignKey('goals.AiGoal', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    insight_text = models.TextField()  # Store the generated insights as text
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Insight for goal: {self.ai_goal.title[:50]}"  # Display part of the goal title
