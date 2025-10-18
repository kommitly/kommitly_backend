import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import Task, SubTask  # ✅ Use correct casing for `SubTask`
from goals.tasks import send_task_reminders, send_subtask_reminders, send_overdue_task_notifications,send_overdue_subtask_notifications  # Assuming it supports subtasks too

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders and overdue notifications for tasks and subtasks'

    def handle(self, *args, **options):
        now_utc = timezone.now()


        # ----- Task reminders -----
        tasks = Task.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)
        self.stdout.write(self.style.SUCCESS(f"🌍 Found {tasks.count()} tasks at {now_utc} UTC"))

        for task in tasks:
            if not task.due_date or not task.reminder_time:
                self.stdout.write(self.style.SUCCESS(f"Either no task due date reminder time  {task.title}"))
                continue

            user = task.user
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)
                
                due_utc = task.due_date  # already UTC aware
                reminder_time_utc = task.reminder_time  # stored as UTC time

                # Combine date + reminder_time (UTC)
                reminder_utc = datetime.combine(due_utc.date(), reminder_time_utc).replace(tzinfo=pytz.UTC)

                # Logging in user local time for clarity
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = due_utc.astimezone(user_timezone)

                logger.debug(
                    f"✅ {task.title}: due_utc={due_utc}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}"
                )


                
                if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                    send_task_reminders(task_id=task.id)
                    #task.reminder_sent = True
                    #task.save(update_fields=["reminder_sent"])
                    self.stdout.write(f"Reminder sent for task: {task.title}")
            except Exception as e:
                logger.error(f"Error sending task reminder: {e}")

        # ----- SubTask reminders -----
        subtasks = SubTask.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False,)
        
        for subtask in subtasks:
            
            if not subtask.due_date or not subtask.reminder_time:
                self.stdout.write(self.style.SUCCESS(f"Either no subtask due date reminder time for {subtask.title} "))
                continue

            # 🛠 Get the user safely — handle subtasks with no parent task
            user = None
            if subtask.task and subtask.task.user:
                user = subtask.task.user
            elif subtask.routine and subtask.routine.user:
                # Optional: if you ever link routines directly to users
                user = subtask.routine.user

            if not user or not user.timezone:
                continue
            

            try:
                user_timezone = pytz.timezone(user.timezone)

                # --- Compute reminder UTC datetime ---
                due_utc = subtask.due_date  # already UTC aware
                reminder_time_utc = subtask.reminder_time  # stored as UTC time

                # Combine date + reminder_time (UTC)
                reminder_utc = datetime.combine(due_utc.date(), reminder_time_utc).replace(tzinfo=pytz.UTC)

                # Logging in user local time for clarity
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = due_utc.astimezone(user_timezone)

                logger.debug(
                    f"✅ {subtask.title}: due_utc={due_utc}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}"
                )

                
                if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                    send_subtask_reminders(subtask_id=subtask.id)
                    #subtask.reminder_sent = True
                    #subtask.save(update_fields=["reminder_sent"])
                    self.stdout.write(f"Reminder sent for subtask: {subtask.title}")
            except Exception as e:
                logger.error(f"Error sending subtask reminder: {e}")

      
        # ----- Overdue Tasks -----
        overdue_tasks = Task.objects.filter(
            status__in=["pending", "in-progress", "overdue"],
            due_date__lte=now_utc,
            overdue_notified=False
        )
        for task in overdue_tasks:
            self.stdout.write(self.style.SUCCESS(f"🌍 Found the following overdue tasks {task.title} tasks at {now_utc} UTC"))



            if not task.due_date:
                self.stdout.write(self.style.SUCCESS(f"🌍 Found no task due date for {task.title}"))

                continue

            user = task.user
            if not user or not user.timezone:
                continue


            try:
                
            
                user_tz = pytz.timezone(user.timezone)
                now_local = now_utc.astimezone(user_tz)
                due_local = task.due_date.astimezone(user_tz)
                self.stdout.write(self.style.SUCCESS(f"🌍 Now local is: {now_local} and due local is: {due_local} for task {task.title} at {now_utc} UTC"))


                if now_local >= due_local:
                    send_overdue_task_notifications(task_id=task.id)
                    self.stdout.write(f"Overdue notification sent for Task: {task.title}")

            except Exception as e:
                logger.error(f"Error sending overdue task notification: {e}")

        # ----- Overdue SubTasks -----
        overdue_subtasks = SubTask.objects.filter(
            status__in=["pending", "in-progress","overdue"],
            due_date__lt=now_utc,
            overdue_notified=False
        )
        for subtask in overdue_subtasks:

            if not subtask.due_date:
                continue

            user = None
            if subtask.task and subtask.task.user:
                user = subtask.task.user
            elif subtask.routine and subtask.routine.user:
                user = subtask.routine.user

            if not user or not user.timezone:
                continue


            try:
            
                user_tz = pytz.timezone(user.timezone)
                now_local = now_utc.astimezone(user_tz)
                due_local = subtask.due_date.astimezone(user_tz)

                if now_local >= due_local:
                    send_overdue_subtask_notifications(subtask_id=subtask.id)
                    self.stdout.write(f"Overdue notification sent for AI subtask: {subtask.title}")

            except Exception as e:
                logger.error(f"Error sending overdue task notification: {e}")

