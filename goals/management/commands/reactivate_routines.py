from datetime import datetime, time, timedelta, timezone as dt_timezone
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware
from goals.models import Routine, AiSubTask, SubTask, Task


def reset_instance(instance, due_datetime, reminder_datetime):
    """
    Reset the instance for today's cycle.
    Skip resetting COMPLETED or IN-PROGRESS items to avoid overwriting active work.
    Pending/Overdue items get reset to pending for the new cycle.
    """
    if instance.status in ["completed", "in-progress"]:
        return

    instance.status = "pending"
    instance.completed_at = None
    instance.due_date = due_datetime
    instance.reminder_time = reminder_datetime
    instance.reminder_sent = False
    instance.overdue_reason = None
    instance.overdue_notified = False
    instance.save()


class Command(BaseCommand):
    help = "Reactivates AiSubTasks, SubTasks, and Tasks linked to active routines, updating due dates for the current cycle."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Starting daily Reactivate Routines check..."))
        
        # Use UTC today
        now_utc = timezone.now()
        today = now_utc.date()
        self.stdout.write(self.style.SUCCESS(f"DEBUG: Today (UTC) is {today}"))

        # Get all active routines whose start_date <= today
        routines = Routine.objects.filter(is_active=True, start_date__lte=today)
        self.stdout.write(self.style.SUCCESS(f"DEBUG: Found {routines.count()} active routines"))

        for routine in routines:
            self.stdout.write(self.style.SUCCESS(f"DEBUG: Processing routine {routine.id} - {routine.subtask_template_title}"))

            # Skip if past end_date
            if routine.end_date and today > routine.end_date:
                self.stdout.write(f"Skipping routine {routine.id}: past end_date")
                continue

            # ✅ Skip if already reset today
            if routine.last_reset and routine.last_reset >= today:
                self.stdout.write(self.style.WARNING(f"Skipping routine {routine.id}: already reset today ({routine.last_reset})"))
                continue

            # Determine if routine triggers today
            should_trigger = False
            if routine.frequency == "daily":
                should_trigger = True
            elif routine.frequency == "weekly" and routine.day_of_week is not None:
                if today.weekday() == routine.day_of_week:
                    should_trigger = True
            elif routine.frequency == "monthly" and today.day == 1:
                should_trigger = True
            elif routine.frequency == "custom" and routine.custom_interval and routine.custom_unit:
                next_trigger = routine.start_date
                while next_trigger <= today:
                    if next_trigger == today:
                        should_trigger = True
                        break
                    if routine.custom_unit == "days":
                        next_trigger += timedelta(days=routine.custom_interval)
                    elif routine.custom_unit == "weeks":
                        next_trigger += timedelta(weeks=routine.custom_interval)
                    elif routine.custom_unit == "months":
                        next_trigger += relativedelta(months=routine.custom_interval)

            if not should_trigger:
                self.stdout.write(f"Routine {routine.id} does not trigger today")
                continue

            # --- Today’s due and reminder datetimes (UTC aware) ---
            due_utc_today = make_aware(datetime.combine(today, routine.time_of_day or time(8, 0)), timezone=dt_timezone.utc)
            reminder_utc_today = make_aware(datetime.combine(today, routine.reminder_time or time(8, 0)), timezone=dt_timezone.utc)

            self.stdout.write(self.style.SUCCESS(f"due date utc today is : {due_utc_today}"))
            self.stdout.write(self.style.SUCCESS(f"reminder utc today is : {reminder_utc_today}"))

            # --- Reactivate existing AiSubTasks ---
            for ai_subtask in routine.ai_subtasks.all():
                if not ai_subtask.due_date:
                    self.stdout.write(self.style.WARNING(f"[AiSubTask] Skipped (no due_date): {ai_subtask.title}"))
                    continue
                if ai_subtask.due_date.date() <= today - timedelta(days=1):
                    reset_instance(ai_subtask, due_utc_today, reminder_utc_today)
                    self.stdout.write(self.style.SUCCESS(f"[AiSubTask] Reactivated: {ai_subtask.title}"))

            # --- Reactivate existing SubTasks ---
            for subtask in routine.subtasks.all():
                if not subtask.due_date:
                    self.stdout.write(self.style.WARNING(f"[SubTask] Skipped (no due_date): {subtask.title}"))
                    continue
                if subtask.due_date.date() <= today - timedelta(days=1):
                    reset_instance(subtask, due_utc_today, reminder_utc_today)
                    self.stdout.write(self.style.SUCCESS(f"[SubTask] Reactivated: {subtask.title}"))

            # --- Reactivate existing Tasks ---
            for task in routine.tasks.all():
                if not task.due_date:
                    self.stdout.write(self.style.WARNING(f"[Task] Skipped (no due_date): {task.title}"))
                    continue
                if task.due_date.date() <= today - timedelta(days=1):
                    reset_instance(task, due_utc_today, reminder_utc_today)
                    self.stdout.write(self.style.SUCCESS(f"[Task] Reactivated: {task.title}"))

            # --- Create fallback AiSubTask if none exist today ---
            if getattr(routine, "subtask_template_title", None):
                today_ai_titles = routine.ai_subtasks.filter(due_date__date=today).values_list("title", flat=True)
                if routine.subtask_template_title not in today_ai_titles:
                    ai_task = getattr(routine, "ai_task", None)
                    new_ai = AiSubTask.objects.create(
                        title=routine.subtask_template_title,
                        description=getattr(routine, "subtask_template_description", "") or "",
                        due_date=due_utc_today,
                        reminder_time=reminder_utc_today,
                        routine=routine,
                        status="pending",
                        ai_task=ai_task,
                    )
                    self.stdout.write(self.style.SUCCESS(f"[AiSubTask] CREATED (fallback): {new_ai.title}"))

            # --- Create fallback SubTask if none exist today ---
            today_sub_titles = routine.subtasks.filter(due_date__date=today).values_list("title", flat=True)
            if getattr(routine, "subtask_template_title", None) and routine.subtask_template_title not in today_sub_titles:
                new_sub = SubTask.objects.create(
                    title=routine.subtask_template_title,
                    description=getattr(routine, "subtask_template_description", "") or "",
                    due_date=due_utc_today,
                    reminder_time=reminder_utc_today,
                    routine=routine,
                    status="pending",
                )
                self.stdout.write(self.style.SUCCESS(f"[SubTask] CREATED (fallback): {new_sub.title}"))

            # --- Create fallback Task if none exist today ---
            if getattr(routine, "task_template_title", None):
                today_task_titles = routine.tasks.filter(due_date__date=today).values_list("title", flat=True)
                if routine.task_template_title not in today_task_titles:
                    new_task = Task.objects.create(
                        title=routine.task_template_title,
                        description=getattr(routine, "task_template_description", "") or "",
                        due_date=due_utc_today,
                        reminder_time=reminder_utc_today,
                        routine=routine,
                        status="pending",
                    )
                    self.stdout.write(self.style.SUCCESS(f"[Task] CREATED (fallback): {new_task.title}"))

            # ✅ Mark routine as reset today
            routine.last_reset = today
            routine.save(update_fields=["last_reset"])
            self.stdout.write(self.style.SUCCESS(f"Routine {routine.id} marked as reset for {today}"))
