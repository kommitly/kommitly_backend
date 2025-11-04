import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import Task, SubTask
from goals.tasks import (
    send_task_reminders,
    send_subtask_reminders,
    send_overdue_task_notifications,
    send_overdue_subtask_notifications,
)

logger = logging.getLogger(__name__)

REMINDER_WINDOW_MINUTES = 5


class Command(BaseCommand):
    help = 'Send reminders and overdue notifications for tasks and subtasks'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting Task reminder check..."))

        now_utc = timezone.now()
        past_utc = now_utc - timedelta(minutes=REMINDER_WINDOW_MINUTES)

        # ==================== TASK REMINDERS ====================
        tasks = Task.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)
        self.stdout.write(self.style.SUCCESS(f"🌍 Found {tasks.count()} tasks at {now_utc} UTC"))

        for task in tasks:
            if not task.reminder_time:
                self.stdout.write(self.style.WARNING(f"Skipping '{task.title}' — no reminder_time"))
                continue

            user = task.user
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)

                if task.due_date:
                    date_component = task.due_date.date()
                    due_utc = task.due_date
                else:
                    date_component = now_utc.date()
                    due_utc = None

                # Combine reminder_time + date
                reminder_utc = datetime.combine(date_component, task.reminder_time).replace(tzinfo=pytz.UTC)
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = due_utc.astimezone(user_timezone) if due_utc else None

                logger.debug(
                    f"✅ {task.title}: due_utc={due_utc}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}"
                )

                # Within reminder window
                if past_utc <= reminder_utc <= now_utc:
                    send_task_reminders(task_id=task.id)
                    self.stdout.write(self.style.SUCCESS(f"📩 Reminder sent for task: {task.title}"))

            except Exception as e:
                logger.error(f"Error sending task reminder for '{task.title}': {e}")

        # ==================== SUBTASK REMINDERS ====================
        subtasks = SubTask.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)

        for subtask in subtasks:
            if not subtask.reminder_time:
                self.stdout.write(self.style.WARNING(f"Skipping '{subtask.title}' — no reminder_time"))
                continue

            user = None
            if subtask.task and subtask.task.user:
                user = subtask.task.user
            elif subtask.routine and subtask.routine.user:
                user = subtask.routine.user

            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)

                if subtask.due_date:
                    date_component = subtask.due_date.date()
                    due_utc = subtask.due_date
                else:
                    date_component = now_utc.date()
                    due_utc = None

                reminder_utc = datetime.combine(date_component, subtask.reminder_time).replace(tzinfo=pytz.UTC)
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = due_utc.astimezone(user_timezone) if due_utc else None

                logger.debug(
                    f"✅ {subtask.title}: due_utc={due_utc}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}"
                )

                if past_utc <= reminder_utc <= now_utc:
                    send_subtask_reminders(subtask_id=subtask.id)
                    self.stdout.write(self.style.SUCCESS(f"📩 Reminder sent for subtask: {subtask.title}"))

            except Exception as e:
                logger.error(f"Error sending subtask reminder for '{subtask.title}': {e}")

        # ==================== OVERDUE TASKS ====================
        overdue_tasks = Task.objects.filter(
            status__in=["pending", "in-progress", "overdue"],
            due_date__lte=now_utc,
            overdue_notified=False,
        )

        for task in overdue_tasks:
            if not task.due_date:
                continue

            user = task.user
            if not user or not user.timezone:
                continue

            try:
                user_tz = pytz.timezone(user.timezone)
                now_local = now_utc.astimezone(user_tz)
                due_local = task.due_date.astimezone(user_tz)

                if now_local >= due_local:
                    send_overdue_task_notifications(task_id=task.id)
                    self.stdout.write(self.style.SUCCESS(f"⚠️ Overdue notification sent for task: {task.title}"))

            except Exception as e:
                logger.error(f"Error sending overdue task notification for '{task.title}': {e}")

        # ==================== OVERDUE SUBTASKS ====================
        overdue_subtasks = SubTask.objects.filter(
            status__in=["pending", "in-progress", "overdue"],
            due_date__lt=now_utc,
            overdue_notified=False,
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
                    self.stdout.write(self.style.SUCCESS(f"⚠️ Overdue notification sent for subtask: {subtask.title}"))

            except Exception as e:
                logger.error(f"Error sending overdue subtask notification for '{subtask.title}': {e}")
