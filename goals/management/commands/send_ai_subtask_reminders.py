import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import AiSubTask
from goals.tasks import send_ai_subtask_reminders, send_overdue_ai_subtask_notifications

logger = logging.getLogger(__name__)

REMINDER_WINDOW_MINUTES = 5

class Command(BaseCommand):
    help = 'Send reminders for AI subtasks with a due reminder_time'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting ai subtask reminder check..."))
        
        now_utc = timezone.now()

        past_utc = now_utc - timedelta(minutes=REMINDER_WINDOW_MINUTES)

        # --- Pending reminders ---
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

                # --- Compute reminder UTC datetime ---
                due_utc = ai_subtask.due_date  # already UTC aware
                reminder_time_utc = ai_subtask.reminder_time  # stored as UTC time

                # Combine date + reminder_time (UTC)
                reminder_utc = datetime.combine(due_utc.date(), reminder_time_utc).replace(tzinfo=pytz.UTC)

                # Logging in user local time for clarity
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = due_utc.astimezone(user_timezone)

                logger.debug(
                    f"✅ {ai_subtask.title}: due_utc={due_utc}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}"
                )

                # Check if reminder is due (within 2-minute window)
                if past_utc <= reminder_utc <= now_utc:
                    send_ai_subtask_reminders(subtask_id=ai_subtask.id)
                    self.stdout.write(f"[{now_utc:%Y-%m-%d %H:%M:%S}] Reminder sent for AI subtask: {ai_subtask.title}")

            except Exception as e:
                logger.error(f"Error sending reminder for subtask '{ai_subtask.title}': {str(e)}")

        # --- Overdue subtasks ---
        overdue_ai_subtasks = AiSubTask.objects.filter(
            status__in=["pending", "in-progress", "overdue"],
            overdue_notified=False
        )

        for ai_subtask in overdue_ai_subtasks:
            if not ai_subtask.due_date:
                continue

            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            if not user or not user.timezone:
                continue

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
