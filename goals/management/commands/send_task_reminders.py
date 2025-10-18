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
        tasks = Task.objects.filter(status='pending', reminder_sent=False)
        for task in tasks:
            if not task.due_date or not task.reminder_time:
                continue

            try:
                due_utc = task.due_date  # already UTC aware
                reminder_time_utc = task.reminder_time  # stored as UTC time

                # Combine date + reminder_time (UTC)
                reminder_dt_utc = datetime.combine(due_utc.date(), reminder_time_utc).replace(tzinfo=pytz.UTC)


                
                if reminder_dt_utc <= now_utc <= reminder_dt_utc + timedelta(minutes=2):
                    send_task_reminders(task_id=task.id)
                    task.reminder_sent = True
                    task.save(update_fields=["reminder_sent"])
                    self.stdout.write(f"Reminder sent for task: {task.title}")
            except Exception as e:
                logger.error(f"Error sending task reminder: {e}")

        # ----- SubTask reminders -----
        subtasks = SubTask.objects.filter(status='pending', reminder_sent=False)
        for subtask in subtasks:
            if not subtask.due_date or not subtask.reminder_time:
                continue

            try:
                # due_date and reminder_time are stored in UTC already
                reminder_dt_utc = datetime.combine(
                    subtask.due_date, subtask.reminder_time
                ).replace(tzinfo=pytz.UTC)

                if reminder_dt_utc <= now_utc <= reminder_dt_utc + timedelta(minutes=2):
                    send_subtask_reminders(task_id=subtask.id)
                    subtask.reminder_sent = True
                    subtask.save(update_fields=["reminder_sent"])
                    self.stdout.write(f"Reminder sent for subtask: {subtask.title}")
            except Exception as e:
                logger.error(f"Error sending subtask reminder: {e}")

      
        # ----- Overdue Tasks -----
        overdue_tasks = Task.objects.filter(
            status__in=["pending", "in-progress"],
            due_date__lt=now_utc,
            overdue_notified=False
        )
        for task in overdue_tasks:
            try:
                if task.status == "completed":
                    continue

                # Mark overdue + set reason
                if task.status == "pending":
                    task.overdue_reason = "not_started"
                elif task.status == "in-progress":
                    task.overdue_reason = "unfinished"

                task.status = "overdue"
                task.overdue_notified = True
                task.save(update_fields=["status", "overdue_reason", "overdue_notified"])

                send_overdue_task_notifications(task_id=task.id)
                self.stdout.write(f"⚠️ Overdue notification sent for task: {task.title}")
            except Exception as e:
                logger.error(f"Error sending overdue task notification: {e}")

        # ----- Overdue SubTasks -----
        overdue_subtasks = SubTask.objects.filter(
            status__in=["pending", "in-progress"],
            due_date__lt=now_utc,
            overdue_notified=False
        )
        for subtask in overdue_subtasks:
            try:
                send_overdue_subtask_notifications(subtask_id=subtask.id)
                self.stdout.write(f"⚠️ Overdue notification sent for subtask: {subtask.title}")
            except Exception as e:
                logger.error(f"Error sending overdue subtask notification: {e}")

