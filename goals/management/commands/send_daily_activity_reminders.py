from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
import time, pytz

from goals.models import DailyActivity, Task, AiSubTask
from notifications.models import Notification

time.sleep(10)

class Command(BaseCommand):
    help = "Send reminders for upcoming daily activities"

    def handle(self, *args, **options):
        now_utc = timezone.now()
        window = timedelta(minutes=5)  # tolerance window

        activities = DailyActivity.objects.filter(reminder_sent=False, template__is_active=True)

        for activity in activities:
            user = activity.template.user
            if not user or not hasattr(user, "timezone"):
                continue

            # Handle user timezone
            try:
                user_tz = pytz.timezone(user.timezone)
            except Exception:
                user_tz = pytz.UTC

            today = timezone.localdate()
            start_local = datetime.combine(today, activity.start_time)
            start_local = user_tz.localize(start_local)
            start_utc = start_local.astimezone(pytz.UTC)

            if start_utc <= now_utc <= start_utc + window:
                message = f"⏰ Reminder: {activity.title} is starting now!"

                # Identify linked object (Task or AiSubTask)
                linked_object = None
                link = None

                if getattr(activity, "task", None):
                    linked_object = activity.task
                    link = f"https://kommitly-frontend.vercel.app/dashboard/tasks/{linked_object.id}/"

                elif getattr(activity, "ai_subtask", None):
                    linked_object = activity.ai_subtask
                    link = f"https://kommitly-frontend.vercel.app/dashboard/ai-subtasks/{linked_object.id}/"

                # Prepare notification data
                notification_data = {
                    "user": user,
                    "message": message,
                    "type": "reminder",
                    "link": link,
                }

                if linked_object:
                    content_type = ContentType.objects.get_for_model(linked_object)
                    notification_data.update({
                        "content_type": content_type,
                        "object_id": linked_object.id,
                    })

                Notification.objects.create(**notification_data)

                # Optional email reminder
                if user.email:
                    send_mail(
                        subject=f"Reminder: {activity.title} starting soon",
                        message=f"Your activity '{activity.title}' starts now.",
                        from_email="no-reply@kommitly.com",
                        recipient_list=[user.email],
                    )

                activity.reminder_sent = True
                activity.save()
                self.stdout.write(self.style.SUCCESS(f"Reminder sent for {activity.title}")))
