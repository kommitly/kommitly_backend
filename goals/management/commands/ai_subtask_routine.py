from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from datetime import datetime, time
from goals.models import Routine, AiSubTask, SubTask, Task


def reset_instance(instance, due_datetime, reminder_time):
    instance.status = 'pending'
    instance.completed_at = None
    instance.due_date = due_datetime
    instance.reminder_time = reminder_time
    instance.reminder_sent = False
    instance.save()


class Command(BaseCommand):
    help = "Reactivate AiSubTasks, SubTasks, and Tasks (with no subtasks) based on routines"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        today = now.date()

        routines = Routine.objects.filter(is_active=True, start_date__lte=today)
        for routine in routines:
            if routine.end_date and routine.end_date < today:
                continue

            should_trigger = False
            if routine.frequency == "daily":
                should_trigger = True
            elif routine.frequency == "weekly" and today.weekday() == routine.day_of_week:
                should_trigger = True
            elif routine.frequency == "monthly" and today.day == 1:
                should_trigger = True

            elif routine.frequency == "custom":
                if routine.custom_interval and routine.custom_unit:
                    last_trigger_date= routine.start_date
                    while last_trigger_date <= today:
                        if last_trigger_date == today:
                            should_trigger = True
                            break
                        if routine.custom_unit == "days":
                            last_trigger_date += timedelta(days=routine.custom_interval)
                        elif routine.custom_unit == "weeks":
                            last_trigger_date += timedelta(weeks=routine.custom_interval)
                        elif routine.custom_unit == "months":
                            last_trigger_date += relativedelta(months=routine.custom_interval)


            if not should_trigger:
                continue

            due_datetime = timezone.make_aware(datetime.combine(today, routine.time_of_day or time(8, 0)))
            reminder_time = routine.reminder_time or time(8, 0)

             # Reactivate subtasks and tasks

            # 1. AiSubTasks
            for ai_subtask in routine.ai_subtasks.filter(status='completed'):
                reset_instance(ai_subtask, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[AiSubTask] Reactivated: {ai_subtask.title}"))

            # 2. SubTasks
            for subtask in routine.subtasks.filter(status='completed'):
                reset_instance(subtask, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[SubTask] Reactivated: {subtask.title}"))

            # 3. Tasks (only if they have no subtasks)
            for task in routine.tasks.filter(status='completed'):
                reset_instance(task, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[Task] Reactivated: {task.title}"))
