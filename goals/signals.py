from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import AiSubTask, AiTask, AiGoal  # Make sure to import your models

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
