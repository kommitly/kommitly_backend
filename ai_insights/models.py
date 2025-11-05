from django.db import models

# Create your models here.

class AIInsight(models.Model):
    ai_goal = models.ForeignKey('goals.AiGoal', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    ai_task = models.ForeignKey('goals.AiTask', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    ai_subtask = models.ForeignKey('goals.AiSubTask', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    task = models.ForeignKey('goals.Task', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    subtask = models.ForeignKey('goals.SubTask', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='insights', null=True, blank=True)  
    insight_text = models.TextField()  # Store the generated insights as text
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.ai_subtask:
            return f"Insight for AI Subtask: {self.ai_subtask.title}"
        elif self.ai_task:
            return f"Insight for AI Task: {self.ai_task.title}"
        elif self.ai_goal:
            return f"Insight for AI Goal: {self.ai_goal.title}"
        elif self.task:
            return f"Insight for Task: {self.task.title}"
        elif self.subtask:
            return f"Insight for Subtask: {self.subtask.title}"
        return "Insight (unlinked)"