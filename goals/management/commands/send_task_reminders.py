import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import Task, SubTask  # ✅ Use correct casing for `SubTask`
from goals.tasks import send_task_reminders, send_subtask_reminders, send_overdue_task_notifications,send_overdue_subtask_notifications  # Assuming it supports subtasks too

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for tasks and their subtasks with a due reminder_time'

    def handle(self, *args, **options):
        now_utc = timezone.now()

        # ----- Task reminders -----
        tasks = Task.objects.filter(status='pending', reminder_sent=False)
        for task in tasks:
            if not task.due_date or not task.reminder_time:
                continue

            user = task.user
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)
                reminder_local = datetime.combine(task.due_date, task.reminder_time)
                reminder_localized = user_timezone.localize(reminder_local)
                reminder_utc = reminder_localized.astimezone(pytz.UTC)

                if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                    send_task_reminders(task_id=task.id)
                    task.reminder_sent = True
                    task.save()
                    self.stdout.write(f"Reminder sent for task: {task.title}")
            except Exception as e:
                logger.error(f"Error sending task reminder: {e}")

        # ----- SubTask reminders -----
        subtasks = SubTask.objects.filter(status='pending', reminder_sent=False)
        for subtask in subtasks:
            if not subtask.due_date or not subtask.reminder_time:
                continue

            user = subtask.task.user if subtask.task else None
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)
                reminder_local = datetime.combine(subtask.due_date, subtask.reminder_time)
                reminder_localized = user_timezone.localize(reminder_local)
                reminder_utc = reminder_localized.astimezone(pytz.UTC)

                if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                    send_subtask_reminders(task_id=subtask.id)  # or use a different method
                    subtask.reminder_sent = True
                    subtask.save()
                    self.stdout.write(f"Reminder sent for subtask: {subtask.title}")
            except Exception as e:
                logger.error(f"Error sending subtask reminder: {e}")


        # ----- Overdue Tasks -----
        overdue_tasks = Task.objects.filter(
            status__in=["pending", "in_progress"],
            due_date__lt=now_utc.date(),
            overdue_notified=False 
        )
        for task in overdue_tasks:
            try:
                if task.status == "completed":
                    continue  # ✅ don't notify completed tasks

                # set overdue status + reason
                if task.status == "pending":
                    task.overdue_reason = "not_started"
                elif task.status == "in_progress":
                    task.overdue_reason = "unfinished"

                task.status = "overdue"
                task.overdue_notified = True 
                task.save(update_fields=["status", "overdue_reason", "overdue_notified"])

                send_overdue_task_notifications(task_id=task.id)
                self.stdout.write(f"Overdue notification sent for task: {task.title}")
            except Exception as e:
                logger.error(f"Error sending overdue task notification: {e}")

        # ----- Overdue SubTasks -----
        overdue_subtasks = SubTask.objects.filter(
            status__in=["pending", "in_progress"],
            due_date__lt=now_utc.date()
            
        )
        for subtask in overdue_subtasks:
            try:
                send_overdue_subtask_notifications(subtask_id=subtask.id)
                self.stdout.write(f"Overdue notification sent for subtask: {subtask.title}")
            except Exception as e:
                logger.error(f"Error sending overdue subtask notification: {e}")
