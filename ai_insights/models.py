from django.db import models

# Create your models here.

class AIInsight(models.Model):
    goal = models.ForeignKey('goals.Goal', on_delete=models.CASCADE, related_name='insights')
    insight_text = models.TextField()  # Store the generated insights as text
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Insight for goal: {self.goal.title[:50]}"  # Display part of the goal title
