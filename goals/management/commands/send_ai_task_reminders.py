import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import AiTask
from goals.tasks import send_ai_task_reminders  # your function already defined

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for AI tasks with a due reminder_time'

    def handle(self, *args, **options):
        now_utc = timezone.now()
        ai_tasks = AiTask.objects.filter(status='pending', reminder_sent=False)

        for ai_task in ai_tasks:
            if not ai_task.due_date or not ai_task.reminder_time:
                continue

            user = ai_task.user or (ai_task.goal.user if ai_task.goal else None)
            if not user:
                continue

            user_timezone = pytz.timezone(user.timezone)
            reminder_local = datetime.combine(ai_task.due_date, ai_task.reminder_time)
            reminder_localized = user_timezone.localize(reminder_local)
            reminder_utc = reminder_localized.astimezone(pytz.UTC)

            if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                send_ai_task_reminders(task_id=ai_task.id)
                self.stdout.write(f"Reminder sent for AI task: {ai_task.title}")
        
        self.stdout.write("AI task reminder check complete.")
