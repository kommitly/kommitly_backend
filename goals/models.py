from django.db import models

# Create your models here.
class Goal(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class AiGoal(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ai_goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



class Task(models.Model):
    goal = models.ForeignKey(Goal, related_name='tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True) 
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('overdue', 'Overdue'),
        ],
        default='pending',
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    actionable_steps = models.JSONField(default=dict)  # Add this field
    task_timeline = models.CharField(max_length=255, null=True, blank=True)  # Add this field
    
    def __str__(self):
        return self.title

class AiTask(models.Model):
    ai_goal = models.ForeignKey(AiGoal, related_name='ai_tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True) 
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('overdue', 'Overdue'),
        ],
        default='pending',
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    actionable_steps = models.JSONField(default=dict)  # Add this field
    task_timeline = models.CharField(max_length=255, null=True, blank=True)  # Add this field
    
    def __str__(self):
        return self.title
