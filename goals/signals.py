from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
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


# -------- Routine ↔ AiSubTask (FIXED) --------

@receiver(post_save, sender=Routine)
def sync_routine_reminder_to_ai_subtasks(sender, instance, **kwargs):
    # 1. Check for the recursion flag
    if kwargs.get('skip_sync'):
        return

    if instance.reminder_time:
        for ai_subtask in instance.ai_subtasks.all():
            if ai_subtask.reminder_time != instance.reminder_time:
                ai_subtask.reminder_time = instance.reminder_time
                # 2. Pass the flag when saving the linked object
                ai_subtask.save(update_fields=["reminder_time"], skip_sync=True)

@receiver(post_save, sender=AiSubTask)
def sync_ai_subtask_reminder_to_routine(sender, instance, **kwargs):
    # 1. Check for the recursion flag
    if kwargs.get('skip_sync'):
        return

    if instance.reminder_time and instance.routine:
        if instance.routine.reminder_time != instance.reminder_time:
            instance.routine.reminder_time = instance.reminder_time
            # 2. Pass the flag when saving the linked object
            instance.routine.save(update_fields=["reminder_time"], skip_sync=True)

# ----------------------------------------------
# ----------------------------------------------

# -------- Routine ↔ Task (FIXED) --------
@receiver(post_save, sender=Routine)
def sync_routine_reminder_to_tasks(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return
        
    if instance.reminder_time:
        for task in instance.tasks.all():
            if task.reminder_time != instance.reminder_time:
                task.reminder_time = instance.reminder_time
                task.save(update_fields=["reminder_time"], skip_sync=True)

@receiver(post_save, sender=Task)
def sync_task_reminder_to_routine(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.reminder_time and instance.routine:
        if instance.routine.reminder_time != instance.reminder_time:
            instance.routine.reminder_time = instance.reminder_time
            instance.routine.save(update_fields=["reminder_time"], skip_sync=True)

# ----------------------------------------------
# ----------------------------------------------

# -------- Routine ↔ SubTask (FIXED) --------
@receiver(post_save, sender=Routine)
def sync_routine_reminder_to_subtasks(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.reminder_time:
        for subtask in instance.subtasks.all():
            if subtask.reminder_time != instance.reminder_time:
                subtask.reminder_time = instance.reminder_time
                subtask.save(update_fields=["reminder_time"], skip_sync=True)

@receiver(post_save, sender=SubTask)
def sync_subtask_reminder_to_routine(sender, instance, **kwargs):
    if kwargs.get('skip_sync'):
        return

    if instance.reminder_time and instance.routine:
        if instance.routine.reminder_time != instance.reminder_time:
            instance.routine.reminder_time = instance.reminder_time
            instance.routine.save(update_fields=["reminder_time"], skip_sync=True)

# ----------------------------------------------