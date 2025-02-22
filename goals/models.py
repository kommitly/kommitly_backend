from django.db import models
from django.utils.timezone import now

# Create your models here.
class Goal(models.Model):
    CATEGORY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('priority', 'Priority'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, null=True, blank=True
    )
    progress = models.IntegerField(default=0)  # Added progress field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class AiGoal(models.Model):
    CATEGORY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('priority', 'Priority'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ai_goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, null=True, blank=True
    ) 
    progress = models.IntegerField(default=0)  # Added progress field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_progress(self):
        """
        Update the progress percentage based on completed tasks.
        """
        total_tasks = self.ai_tasks.count()
        completed_tasks = self.ai_tasks.filter(status='completed').count()

        if total_tasks > 0:
            self.progress = int((completed_tasks / total_tasks) * 100)
        else:
            self.progress = 0  # No tasks yet, so progress remains 0%

        self.save()

        def __str__(self):
            return self.title

class Task(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)  
    goal = models.ForeignKey(Goal, related_name='tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)

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
    actionable_steps = models.JSONField(default=dict)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class AiTask(models.Model):
    ai_goal = models.ForeignKey(AiGoal, related_name='ai_tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)

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
    actionable_steps = models.JSONField(default=dict)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Override save method to update goal progress when task status changes.
        """
        is_being_completed = self.status == 'completed' and self.completed_at is None
        if is_being_completed:
            self.completed_at = now()  # Set completion timestamp

        super().save(*args, **kwargs)  # Save task first
        if self.ai_goal:
            self.ai_goal.update_progress()  # Update goal progress

    def __str__(self):
        return self.title
