import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import AiSubTask
from goals.tasks import send_ai_subtask_reminders, send_overdue_ai_subtask_notifications  # Your existing function

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for AI subtasks with a due reminder_time'

    def handle(self, *args, **options):
        now_utc = timezone.now()
        ai_subtasks = AiSubTask.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)
        logger.info(f"Found {ai_subtasks.count()} AI subtasks pending reminders.")

        for ai_subtask in ai_subtasks:
            if not ai_subtask.due_date or not ai_subtask.reminder_time:
                continue

            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)
                # Combine due_date and reminder_time
                reminder_naive = datetime.combine(
                    ai_subtask.due_date.astimezone(user_timezone).date(),
                    ai_subtask.reminder_time
                )

                # Localize to user timezone if naive
                if timezone.is_naive(reminder_naive):
                    reminder_local = user_timezone.localize(reminder_naive)
                else:
                    reminder_local = reminder_naive

                # Convert to UTC
                reminder_utc = reminder_local.astimezone(pytz.UTC)

                # Check if within 2-minute window
                if reminder_utc <= now_utc <= reminder_utc + timedelta(minutes=2):
                    send_ai_subtask_reminders(subtask_id=ai_subtask.id)
                    self.stdout.write(f"Reminder sent for AI subtask: {ai_subtask.title}")
                

            except Exception as e:
                logger.error(f"Error sending reminder for subtask '{ai_subtask.title}': {str(e)}")

        # ----- Overdue AI Subtasks -----
        overdue_ai_subtasks = AiSubTask.objects.filter(
            status__in=["pending", "in-progress"],
            due_date__lte=now_utc,
            overdue_notified=False 
        )
        logger.info(f"Found {overdue_ai_subtasks.count()} AI subtasks to mark overdue.")


        for ai_subtask in overdue_ai_subtasks:
            try:
                user_tz = pytz.timezone(user.timezone)
                now_local = now_utc.astimezone(user_tz)
                due_local = ai_subtask.due_date.astimezone(user_tz)
                

                if now_local >= due_local:
                    send_overdue_ai_subtask_notifications(subtask_id=ai_subtask.id)
                    self.stdout.write(f"Overdue notification sent for AI subtask: {ai_subtask.title}")

            except Exception as e:
                logger.error(f"Error sending overdue AI subtask notification: {str(e)}")

        self.stdout.write("AI subtask reminder & overdue check complete.")
