import pytz
from datetime import datetime
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import AiSubTask, AiTask, AiGoal, Routine, SubTask, Task  # Make sure to import your models

# --- Signal 1: When a subtask is saved (created or updated) ---
@receiver(post_save, sender=AiSubTask)
def update_goal_progress_on_subtask_save(sender, instance, created, **kwargs):
    if instance.ai_task and instance.ai_task.ai_goal:
        print(f"DEBUG: post_save signal for AiSubTask '{instance.title}'. Calling AiGoal.update_progress().")
        instance.ai_task.ai_goal.update_progress()
    else:
        print(f"DEBUG: post_save signal for AiSubTask '{instance.title}', but no associated AiTask or AiGoal found.")


# --- Cache the goal before subtask deletion ---
_deleted_ai_goal = {}

@receiver(pre_delete, sender=AiSubTask)
def cache_goal_on_subtask_delete(sender, instance, **kwargs):
    if instance.ai_task and instance.ai_task.ai_goal:
        _deleted_ai_goal[instance.pk] = instance.ai_task.ai_goal


# --- Update progress only if goal still exists ---
@receiver(post_delete, sender=AiSubTask)
def update_goal_progress_on_subtask_delete(sender, instance, **kwargs):
    ai_goal = _deleted_ai_goal.pop(instance.pk, None)
    if ai_goal and AiGoal.objects.filter(pk=ai_goal.pk).exists():
        goal = AiGoal.objects.get(pk=ai_goal.pk)
        goal.update_progress()


# -------- Routine ↔ AiSubTask (Full Sync) --------

@receiver(post_save, sender=Routine)
def sync_routine_to_ai_subtasks(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    routine_time_of_day = instance.time_of_day
    routine_reminder_time = instance.reminder_time
    update_fields = []
    

    for ai_subtask in instance.ai_subtasks.all():
        needs_save = False
        
        # 1. Sync REMINDER TIME
        if routine_reminder_time and ai_subtask.reminder_time != routine_reminder_time:
            ai_subtask.reminder_time = routine_reminder_time
            needs_save = True
            update_fields.append("reminder_time")
        
        # 2. Sync DUE DATE TIME component
        if routine_time_of_day:
            # Get the date component: use the subtask's existing date, or today's date if null
            current_date = ai_subtask.due_date.date() if ai_subtask.due_date else timezone.now().date()
            
            # Combine current date with new time, and make it timezone aware (UTC is safest for DB)
            new_due_date = timezone.make_aware(
                datetime.combine(current_date, routine_time_of_day),
                timezone.get_current_timezone() # Use server's timezone for combining
            ).astimezone(pytz.UTC)

            # Check if the time component has changed
            if ai_subtask.due_date is None or ai_subtask.due_date.time() != routine_time_of_day:
                ai_subtask.due_date = new_due_date
                needs_save = True
                update_fields.append("due_date")
        
        if needs_save:
            # Use list(set(...)) to ensure unique fields
            ai_subtask.save(update_fields=list(set(update_fields)), skip_sync=True)
            update_fields = []


@receiver(post_save, sender=AiSubTask)
def sync_ai_subtask_to_routine(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.routine:
        routine = instance.routine
        needs_save = False
        update_fields = []

        # 1. Sync REMINDER TIME
        if instance.reminder_time and routine.reminder_time != instance.reminder_time:
            routine.reminder_time = instance.reminder_time
            needs_save = True
            update_fields.append("reminder_time")

        # 2. Sync TIME OF DAY from the subtask's DUE DATE
        if instance.due_date and isinstance(instance.due_date, datetime):
            new_time_of_day = instance.due_date.time() 
            
            if routine.time_of_day != new_time_of_day:
                routine.time_of_day = new_time_of_day
                needs_save = True
                update_fields.append("time_of_day")

        if needs_save:
            routine.save(update_fields=list(set(update_fields)), skip_sync=True)

# ----------------------------------------------
# ----------------------------------------------

# -------- Routine ↔ Task (Full Sync) --------

@receiver(post_save, sender=Routine)
def sync_routine_to_tasks(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    routine_time_of_day = instance.time_of_day
    routine_reminder_time = instance.reminder_time
    update_fields = []

    for task in instance.tasks.all():
        needs_save = False

        # 1. Sync REMINDER TIME
        if routine_reminder_time and task.reminder_time != routine_reminder_time:
            task.reminder_time = routine_reminder_time
            needs_save = True
            update_fields.append("reminder_time")

        # 2. Sync DUE DATE TIME component
        if routine_time_of_day:
            current_date = task.due_date.date() if task.due_date else timezone.now().date()
            
            new_due_date = timezone.make_aware(
                datetime.combine(current_date, routine_time_of_day),
                timezone.get_current_timezone()
            ).astimezone(pytz.UTC)

            if task.due_date is None or task.due_date.time() != routine_time_of_day:
                task.due_date = new_due_date
                needs_save = True
                update_fields.append("due_date")
        
        if needs_save:
            task.save(update_fields=list(set(update_fields)), skip_sync=True)
            update_fields = []

@receiver(post_save, sender=Task)
def sync_task_to_routine(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.routine:
        routine = instance.routine
        needs_save = False
        update_fields = []

        # 1. Sync REMINDER TIME
        if instance.reminder_time and routine.reminder_time != instance.reminder_time:
            routine.reminder_time = instance.reminder_time
            needs_save = True
            update_fields.append("reminder_time")

        # 2. Sync TIME OF DAY
        if instance.due_date and isinstance(instance.due_date, datetime):
            new_time_of_day = instance.due_date.time() 
            
            if routine.time_of_day != new_time_of_day:
                routine.time_of_day = new_time_of_day
                needs_save = True
                update_fields.append("time_of_day")
        
        if needs_save:
            routine.save(update_fields=list(set(update_fields)), skip_sync=True)

# ----------------------------------------------
# ----------------------------------------------

# -------- Routine ↔ SubTask (Full Sync) --------

@receiver(post_save, sender=Routine)
def sync_routine_to_subtasks(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    routine_time_of_day = instance.time_of_day
    routine_reminder_time = instance.reminder_time
    update_fields = []

    for subtask in instance.subtasks.all():
        needs_save = False

        # 1. Sync REMINDER TIME
        if routine_reminder_time and subtask.reminder_time != routine_reminder_time:
            subtask.reminder_time = routine_reminder_time
            needs_save = True
            update_fields.append("reminder_time")

        # 2. Sync DUE DATE TIME component
        if routine_time_of_day:
            current_date = subtask.due_date.date() if subtask.due_date else timezone.now().date()
            
            new_due_date = timezone.make_aware(
                datetime.combine(current_date, routine_time_of_day),
                timezone.get_current_timezone()
            ).astimezone(pytz.UTC)

            if subtask.due_date is None or subtask.due_date.time() != routine_time_of_day:
                subtask.due_date = new_due_date
                needs_save = True
                update_fields.append("due_date")
        
        if needs_save:
            subtask.save(update_fields=list(set(update_fields)), skip_sync=True)
            update_fields = []

@receiver(post_save, sender=SubTask)
def sync_subtask_to_routine(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.routine:
        routine = instance.routine
        needs_save = False
        update_fields = []

        # 1. Sync REMINDER TIME
        if instance.reminder_time and routine.reminder_time != instance.reminder_time:
            routine.reminder_time = instance.reminder_time
            needs_save = True
            update_fields.append("reminder_time")

        # 2. Sync TIME OF DAY
        if instance.due_date and isinstance(instance.due_date, datetime):
            new_time_of_day = instance.due_date.time() 
            
            if routine.time_of_day != new_time_of_day:
                routine.time_of_day = new_time_of_day
                needs_save = True
                update_fields.append("time_of_day")
        
        if needs_save:
            routine.save(update_fields=list(set(update_fields)), skip_sync=True)

# ----------------------------------------------
