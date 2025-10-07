import pytz
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from goals.models import Routine, AiSubTask, SubTask, Task


def reset_instance(instance, due_datetime, reminder_time):
    """Reset the instance for the current routine cycle."""
    instance.status = "pending"
    instance.completed_at = None
    instance.due_date = due_datetime
    instance.reminder_time = reminder_time
    instance.reminder_sent = False
    instance.overdue_reason = None
    instance.overdue_notified = False
    instance.save()


class Command(BaseCommand):
    help = "Reactivates AiSubTasks, SubTasks, and Tasks linked to active routines, updating due dates for the current cycle."

    def handle(self, *args, **kwargs):
        now = timezone.now()
        today = now.date()

        routines = Routine.objects.filter(is_active=True, start_date__lte=today)

        for routine in routines:
            if routine.end_date and today > routine.end_date:
                continue  # Stop processing past the routine’s duration

            # --- Determine if the routine should trigger today ---
            should_trigger = False
            if routine.frequency == "daily":
                should_trigger = True
            elif routine.frequency == "weekly" and today.weekday() == routine.day_of_week:
                should_trigger = True
            elif routine.frequency == "monthly" and today.day == 1:
                should_trigger = True
            elif routine.frequency == "custom":
                if routine.custom_interval and routine.custom_unit:
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
                continue

            # --- Calculate today's due and reminder datetimes ---
            reminder_time_today = datetime.combine(today, routine.reminder_time or time(8, 0))
            due_time_today = datetime.combine(today, routine.time_of_day or time(8, 0))

            reminder_utc_today = timezone.make_aware(reminder_time_today, timezone.get_current_timezone()).astimezone(pytz.UTC)
            due_utc_today = timezone.make_aware(due_time_today, timezone.get_current_timezone()).astimezone(pytz.UTC)

            # --- Reactivate existing linked items ---
            for ai_subtask in routine.ai_subtasks.all():
                reset_instance(ai_subtask, due_utc_today, routine.reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[AiSubTask] Reactivated: {ai_subtask.title}"))

            for subtask in routine.subtasks.all():
                reset_instance(subtask, due_utc_today, routine.reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[SubTask] Reactivated: {subtask.title}"))

            for task in routine.tasks.all():
                reset_instance(task, due_utc_today, routine.reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[Task] Reactivated: {task.title}"))
