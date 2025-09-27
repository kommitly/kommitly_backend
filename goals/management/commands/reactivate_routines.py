import pytz
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from goals.models import Routine, AiSubTask, SubTask, Task


def reset_instance(instance, due_datetime, reminder_time):
    instance.status = 'pending'
    instance.completed_at = None
    instance.due_date = due_datetime
    instance.reminder_time = reminder_time
    instance.reminder_sent = False
    instance.overdue_reason = None
    instance.overdue_notified = False
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

            # Get the routine's reminder time as a datetime for today
            reminder_time_today = datetime.combine(today, routine.reminder_time or time(8, 0))
            reminder_utc_today = timezone.make_aware(reminder_time_today, timezone.get_current_timezone()).astimezone(pytz.UTC)

            # Get the routine's due time as a datetime for today
            due_time_today = datetime.combine(today, routine.time_of_day or time(8, 0))
            due_utc_today = timezone.make_aware(due_time_today, timezone.get_current_timezone()).astimezone(pytz.UTC)

            # If the reminder time has already passed today, schedule it for tomorrow.
            if reminder_utc_today < now:
                # Schedule both the due date and reminder for the next day's occurrence.
                due_datetime = due_utc_today + timedelta(days=1)
                reminder_time = routine.reminder_time or time(8, 0)
            else:
                # Schedule for today as it's still in the future.
                due_datetime = due_utc_today
                reminder_time = routine.reminder_time or time(8, 0)



            if routine.subtask_template_title and routine.frequency == 'daily':
                
                # Check if a task from this template has already been created today.
                # This prevents duplicate subtasks if the cron job runs multiple times a day.
                # We check for a task linked to the routine, with the same title, created TODAY.
                today_subtasks_count = AiSubTask.objects.filter(
                    routine=routine,
                    title=routine.subtask_template_title,
                    # Assumes AiSubTask has a 'created_at' field (standard Django practice)
                    # If not, use 'last_updated' and be careful.
                    # We check if created_at is today's date in the routine's local timezone.
                    # Simplified check: created_at__date should match today
                    created_at__date=today
                ).count()

                if today_subtasks_count == 0:
                    
                    # 1. Determine parent goal/task for linking (Adapt based on your model)
                    # Assuming a foreign key link from Routine to AiGoal (or get it through linked tasks)
                    ai_goal = getattr(routine, 'ai_goal', None) 
                    ai_task = None
                    if routine.ai_subtasks.first(): # Use the first linked task to infer the parent
                         ai_task = getattr(routine.ai_subtasks.first(), 'ai_task', None)

                    # 2. Create the new AiSubTask instance
                    new_subtask = AiSubTask.objects.create(
                        title=routine.subtask_template_title,
                        description=routine.subtask_template_description,
                        due_date=due_datetime,
                        reminder_time=reminder_time,
                        routine=routine,
                        status='pending',
                        ai_task=ai_task, # Link to the parent AiTask
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"[AiSubTask] GENERATED: {new_subtask.title} (ID: {new_subtask.id}) for daily routine {routine.id}"))
                    
                    # IMPORTANT: For a GENERATING routine, we typically don't want to 
                    # execute the reactivation logic below, as it would cause confusion.
                    # We continue to the next routine immediately.
                    continue 




             # Reactivate subtasks and tasks

            # 1. AiSubTasks
            for ai_subtask in routine.ai_subtasks.all():
                reset_instance(ai_subtask, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[AiSubTask] Reactivated: {ai_subtask.title}"))

            # 2. SubTasks
            for subtask in routine.subtasks.all():
                reset_instance(subtask, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[SubTask] Reactivated: {subtask.title}"))

            # 3. Tasks (only if they have no subtasks)
            for task in routine.tasks.all():
                reset_instance(task, due_datetime, reminder_time)
                self.stdout.write(self.style.SUCCESS(f"[Task] Reactivated: {task.title}"))
