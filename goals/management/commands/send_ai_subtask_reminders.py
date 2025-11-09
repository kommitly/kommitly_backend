import pytz
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import AiSubTask # Assuming this is your model
from goals.tasks import send_ai_subtask_reminders, send_overdue_ai_subtask_notifications # Assuming tasks are here

# --- Imports for Email/Notification (Required for send_ai_subtask_reminders) ---
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.contrib.contenttypes.models import ContentType
# Assuming Notification model exists
# from yourapp.models import Notification # Uncomment and replace with your actual import

logger = logging.getLogger(__name__)

REMINDER_WINDOW_MINUTES = 5

class Command(BaseCommand):
    help = 'Send reminders for AI subtasks with a due reminder_time'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting ai subtask reminder check..."))
        
        now_utc = timezone.now()

        # Check for reminders that fell between (now - window) and now
        # This is a backward-looking window to catch reminders that may have been missed
        past_utc = now_utc - timedelta(minutes=REMINDER_WINDOW_MINUTES)

        # --- Pending reminders ---
        # Only consider tasks that haven't sent a reminder yet
        ai_subtasks = AiSubTask.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)
        logger.info(f"Found {ai_subtasks.count()} AI subtasks pending reminders.")

        for ai_subtask in ai_subtasks:
            # Basic sanity check
            if not ai_subtask.due_date or not ai_subtask.reminder_time:
                continue

            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            if not user or not user.timezone:
                continue

            try:
                user_timezone = pytz.timezone(user.timezone)

                # --- Compute reminder UTC datetime ---
                # due_utc is already a date/datetime field in UTC
                due_utc = ai_subtask.due_date.replace(hour=0, minute=0, second=0, microsecond=0) # Reset time components of the date
                reminder_time_utc = ai_subtask.reminder_time  # stored as UTC time (TimeField)

                # Combine the date of the due_utc with the time of the reminder_time_utc
                # This gives the exact UTC moment the reminder should be sent.
                # If due_date is a DateTimeField, ensure you're only using its date component.
                reminder_utc = datetime.combine(due_utc.date(), reminder_time_utc).replace(tzinfo=pytz.UTC)

                # Logging in user local time for clarity
                reminder_local = reminder_utc.astimezone(user_timezone)
                due_local = ai_subtask.due_date.astimezone(user_timezone) if ai_subtask.due_date else 'N/A' # Use due_date directly here

                logger.info(
                    f"✅ {ai_subtask.title}: due_utc={ai_subtask.due_date}, "
                    f"reminder_local={reminder_local}, reminder_utc={reminder_utc}, now_utc={now_utc}, past_utc={past_utc}"
                )

                # Check if reminder is due (reminder_utc falls within the past_utc and now_utc window)
                if past_utc <= reminder_utc <= now_utc:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[{now_utc:%Y-%m-%d %H:%M:%S}] Triggering reminder for AI subtask: {ai_subtask.title}"
                        )
                    )
                    send_ai_subtask_reminders(subtask_id=ai_subtask.id)

            except Exception as e:
                logger.error(f"Error sending reminder for subtask '{ai_subtask.title}': {str(e)}")

        # --- Overdue subtasks ---
        # The logic here seems correct for checking overdue based on local time
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
                # ai_subtask.due_date is a UTC-aware datetime, convert to user's local timezone
                due_local = ai_subtask.due_date.astimezone(user_tz)

                # Check if the current time in the user's timezone is past the due date/time
                if now_local >= due_local:
                    send_overdue_ai_subtask_notifications(subtask_id=ai_subtask.id)
                    self.stdout.write(f"Overdue notification sent for AI subtask: {ai_subtask.title}")

            except Exception as e:
                logger.error(f"Error sending overdue AI subtask notification: {str(e)}")


        self.stdout.write("AI subtask reminder & overdue check complete.")