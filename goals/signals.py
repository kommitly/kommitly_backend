from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AiSubTask, AiTask, AiGoal # Make sure to import your models

@receiver(post_save, sender=AiSubTask)
def update_goal_progress_on_subtask_save(sender, instance, created, **kwargs):
    # This signal fires AFTER an AiSubTask is saved or updated.
    # We ensure that if a subtask is tied to a task and a goal,
    # the goal's progress is recalculated.
    if instance.ai_task and instance.ai_task.ai_goal:
        print(f"DEBUG: post_save signal for AiSubTask '{instance.title}'. Calling AiGoal.update_progress().")
        instance.ai_task.ai_goal.update_progress()
    else:
        print(f"DEBUG: post_save signal for AiSubTask '{instance.title}', but no associated AiTask or AiGoal found.")
        
@receiver(post_delete, sender=AiSubTask)
def update_goal_progress_on_subtask_delete(sender, instance, **kwargs):
    try:
        if instance.ai_task and instance.ai_task.ai_goal:
            print(f"DEBUG: post_delete signal for AiSubTask '{instance.title}'. Calling AiGoal.update_progress().")
            instance.ai_task.ai_goal.update_progress()
        else:
            print(f"DEBUG: post_delete signal for AiSubTask '{instance.title}' deletion, but no associated AiTask or AiGoal found.")
    except AiTask.DoesNotExist:
        print(f"DEBUG: AiTask already deleted for subtask '{instance.title}' — skipping progress update.")
