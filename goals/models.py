from django.db import models
from django.utils.timezone import now, make_aware, is_naive
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.dateparse import parse_datetime

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
    tag= models.CharField(max_length=255, null=True, blank=True)  # Added tag field

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
    tag = models.CharField(max_length=255, null=True, blank=True)  # Added tag field
    

    def update_progress(self):
        total_subtasks = AiSubTask.objects.filter(ai_task__ai_goal=self).count()
        completed_subtasks = AiSubTask.objects.filter(ai_task__ai_goal=self, status='completed').count()

        new_progress = int(completed_subtasks * 100 / total_subtasks) if total_subtasks else 0

        if self.progress != new_progress:
            self.progress = new_progress
            self.save(update_fields=["progress"])
            print(f"DEBUG: AiGoal '{self.title}' progress updated to {self.progress}% (Total: {total_subtasks}, Done: {completed_subtasks})")


    def __str__(self):
        return self.title






class Task(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)  
    goal = models.ForeignKey(Goal, related_name='tasks', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    tag = models.CharField(max_length=255, null=True, blank=True)  # Added tag field
    routine = models.ForeignKey('Routine', related_name='tasks', on_delete=models.CASCADE, null=True, blank=True)

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
    overdue_reason = models.CharField(
        max_length=20,
        choices=[("not_started", "Not Started"), ("unfinished", "Unfinished")],
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)  # Track updates
    ai_answer = models.TextField(null=True, blank=True)


    def save(self, *args, **kwargs):
        """
        Override save method to manage task statuses.
        """
        if isinstance(self.due_date, str):
            try:
                self.due_date = make_aware(datetime.fromisoformat(self.due_date))
            except ValueError:
                pass  # Handle invalid date format if needed

        if isinstance(self.reminder_time, str):
            try:
                self.reminder_time = datetime.strptime(self.reminder_time, "%H:%M:%S").time()
            except ValueError:
                pass

        if self.status == 'completed' and self.completed_at is None:
            self.completed_at = now()

        if self.due_date:
            if now() > self.due_date and self.status in ['pending', 'in-progress']:
                self.status = 'overdue'
            elif now() <= self.due_date and self.status == 'overdue':
                self.status = 'pending'  # or 'in-progress' based on your logic


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
    overdue_reason = models.CharField(
        max_length=20,
        choices=[("not_started", "Not Started"), ("unfinished", "Unfinished")],
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    task_timeline = models.CharField(max_length=255, null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
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


        due = self.due_date

        # Convert string to datetime if needed
        if isinstance(due, str):
            due = parse_datetime(due)

        # Only proceed if due is now a datetime
        if due:
            if is_naive(due):
                due = make_aware(due)

            if now() > due and self.status in ['pending', 'in-progress']:
                self.status = 'overdue'
            elif now() <= due and self.status == 'overdue':
                self.status = 'pending'

        super().save(*args, **kwargs)  # Save the current task


     
     

        if self.ai_goal:
            tasks = list(self.ai_goal.ai_tasks.order_by('id')) # convert to list to use index
            if self in tasks: 
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
            if self.ai_goal.ai_tasks.exists() and not self.ai_goal.ai_tasks.filter(status='in-progress').exists():
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
    due_date = models.DateTimeField(blank=True, null=True)
    reminder_time = models.TimeField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ('in-progress', 'In Progress'), ("completed", "Completed"),  ('overdue', 'Overdue'),], default="pending")
    overdue_reason = models.CharField(
        max_length=20,
        choices=[("not_started", "Not Started"), ("unfinished", "Unfinished")],
        null=True,
        blank=True,
    )
    last_updated = models.DateTimeField(auto_now=True) 
    ai_answer = models.TextField(null=True, blank=True)
    routine = models.ForeignKey('Routine', related_name='subtasks', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.title



class AiSubTask(models.Model):
    ai_task = models.ForeignKey(AiTask, related_name="ai_subtasks", on_delete=models.CASCADE, blank=True, null=True)
    routine = models.ForeignKey('Routine', related_name='ai_subtasks', on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    reminder_time = models.TimeField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ('in-progress', 'In Progress'), ("completed", "Completed"),  ('overdue', 'Overdue'),], default="pending")
    overdue_reason = models.CharField(
        max_length=20,
        choices=[("not_started", "Not Started"), ("unfinished", "Unfinished")],
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True) 
    ai_answer = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Store original status to detect changes *before* saving
        original_status = None
        if self.pk:
            try:
                original_status = AiSubTask.objects.get(pk=self.pk).status
            except AiSubTask.DoesNotExist:
                pass # New object

        # Set completed_at if status changes to 'completed'
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            print(f"DEBUG: Subtask '{self.title}' set to completed, timestamped.")
        elif self.status != 'completed' and self.completed_at:
            # If status changes from completed, clear the timestamp
            self.completed_at = None
            print(f"DEBUG: Subtask '{self.title}' changed from completed, clearing timestamp.")

        super().save(*args, **kwargs) # Save the current status of the subtask

        # --- Post-save logic for parent AiTask status ---
        # This logic runs *after* the subtask has been saved with its new status.
        if self.ai_task:
            all_subtasks = self.ai_task.ai_subtasks.all()
            total_subtasks = all_subtasks.count()
            completed_subtasks = all_subtasks.filter(status='completed').count()

            # Rule 1: If all subtasks are completed, mark parent task as completed
            if total_subtasks > 0 and completed_subtasks == total_subtasks:
                if self.ai_task.status != 'completed': # Prevent unnecessary saves
                    self.ai_task.status = 'completed'
                    self.ai_task.save(update_fields=['status', 'completed_at']) # Explicitly save completed_at
                    print(f"DEBUG: All subtasks for AiTask '{self.ai_task.title}' completed. Setting AiTask status to 'completed'.")
            # Rule 2: If task was completed but now has pending/in-progress subtasks, revert to 'in-progress'
            elif self.ai_task.status == 'completed' and completed_subtasks < total_subtasks:
                self.ai_task.status = 'in-progress'
                self.ai_task.save(update_fields=['status', 'completed_at']) # Clear completed_at if needed
                print(f"DEBUG: AiTask '{self.ai_task.title}' reverted from 'completed' to 'in-progress' due to subtask change.")
            # Rule 3: If task is pending and has any subtasks, set to 'in-progress'
            elif self.ai_task.status == 'pending' and total_subtasks > 0 and completed_subtasks < total_subtasks:
                 self.ai_task.status = 'pending'
                 self.ai_task.save(update_fields=['status'])
                 print(f"DEBUG: AiTask '{self.ai_task.title}' set to 'pending' as subtasks exist.")

    def __str__(self):
        return self.title



class Routine(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    INTERVAL_UNITS = [
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    custom_interval = models.PositiveIntegerField(null=True, blank=True)  # e.g., every 3 days
    custom_unit = models.CharField(max_length=20, choices=INTERVAL_UNITS, null=True, blank=True)

    time_of_day = models.TimeField(null=True, blank=True)  # e.g., 09:00 AM
    day_of_week = models.IntegerField(null=True, blank=True)  # 0=Monday, 6=Sunday
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    subtask_template_title = models.CharField(max_length=255, blank=True, null=True)
    subtask_template_description = models.TextField(blank=True, null=True)
    reminder_time = models.TimeField(null=True, blank=True)  # Time to send reminders



    def __str__(self):
        return f"{self.name} ({self.frequency})"
