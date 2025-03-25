from django.db import models
from django.utils.timezone import now

# Create your models here.
class Goal(models.Model):
    CATEGORY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
      
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
    description = models.TextField(null=True, blank=True)
   
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in-progress', 'In Progress'),
            ('completed', 'Completed'),
            ('overdue', 'Overdue'),
        ],
        default='pending',
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)  # Track updates

    def save(self, *args, **kwargs):
        """
        Override save method to manage task statuses.
        """
        if self.status == 'completed' and self.completed_at is None:
            self.completed_at = now()

        if self.due_date and now() > self.due_date and self.status in ['pending', 'in-progress']:
            self.status = 'overdue'

        super().save(*args, **kwargs)

        

    def __str__(self):
        return self.title




class AiTask(models.Model):
    ai_goal = models.ForeignKey(AiGoal, related_name='ai_tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in-progress', 'In Progress'),
            ('completed', 'Completed'),
            ('overdue', 'Overdue'),
        ],
        default='pending',
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)  # Track updates
    
    def save(self, *args, **kwargs):

        """
        Override save method to manage task statuses.
        """

          # Check if there are any pending subtasks before completing the task
        if self.status == 'completed' and self.ai_subtasks.filter(status='pending').exists():
            raise ValidationError("There are pending subtasks that need to be completed before marking the task as completed.")

        if self.status == 'completed' and self.completed_at is None:
            # Set completion timestamp if the task is completed
            self.completed_at = now()


        # Automatically update overdue tasks
        if self.due_date and now() > self.due_date and self.status in ['pending', 'in-progress']:
            self.status = 'overdue'

        super().save(*args, **kwargs)  # Save the current task


        # If the task is completed, check and mark subtasks as completed
        if self.status == 'completed':
            for subtask in self.ai_subtasks.all():
                if subtask.status != 'completed':
                    break
            else:
                # All subtasks are completed, mark the task as completed
                self.status = 'completed'
                self.save(update_fields=['status', 'completed_at'])



     

        if self.ai_goal:
            tasks = list(self.ai_goal.ai_tasks.order_by('id')) # convert to list to use index

            if self.status == 'completed':
                try:
                    current_index = tasks.index(self)
                    if current_index + 1 < len(tasks):
                        next_task = tasks[current_index + 1]
                        if next_task.status == 'pending':
                            next_task.status = 'in-progress'
                            next_task.save(update_fields=['status'])
                except ValueError: #if the current task is not in the list.
                    pass #do nothing.

            # Ensure only the first task is always in-progress if there are no in progress tasks.
            if not self.ai_goal.ai_tasks.filter(status='in-progress').exists():
                first_task = self.ai_goal.ai_tasks.order_by('id').first()
                if first_task and first_task.status == 'pending':
                    first_task.status = 'in-progress'
                    first_task.save(update_fields=['status'])

    def __str__(self):
        return self.title


class SubTask(models.Model):
    task = models.ForeignKey(Task, related_name="subtasks", on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    reminder_time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("completed", "Completed")], default="pending")

    def __str__(self):
        return self.title



class AiSubTask(models.Model):
    ai_task = models.ForeignKey(AiTask, related_name="ai_subtasks", on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    reminder_time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("completed", "Completed")], default="pending")

    def save(self, *args, **kwargs):

        """
        Override save method for AiSubTask to update parent task and goal progress.
        """
        if self.status == 'completed':
            # If all subtasks are completed, mark parent task as completed
            if all(subtask.status == 'completed' for subtask in self.ai_task.ai_subtasks.all()):
                self.ai_task.status = 'completed'
                self.ai_task.save(update_fields=['status', 'completed_at'])
            
            # Update AiGoal progress
            if self.ai_task.ai_goal:
                self.ai_task.ai_goal.update_progress()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title