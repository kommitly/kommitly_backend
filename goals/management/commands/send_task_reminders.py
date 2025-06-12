import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import Task
from goals.tasks import send_task_reminders

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for tasks with a due reminder_time'

    def handle(self, *args, **options):
        now_utc = timezone.now()
        tasks = Task.objects.filter(status='pending')

        for task in tasks:
            if not task.due_date or not task.reminder_time:
                continue

            user = task.user
            user_timezone = pytz.timezone(user.timezone)

            reminder_local = datetime.combine(task.due_date, task.reminder_time)
            reminder_localized = user_timezone.localize(reminder_local)
            reminder_utc = reminder_localized.astimezone(pytz.UTC)

            # Check if current UTC time is within a 2-min window
            if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                send_task_reminders(task_id=task.id)
                self.stdout.write(f"Reminder sent for task: {task.title}")

        else:
            self.stdout.write("No reminders due at this time.")
