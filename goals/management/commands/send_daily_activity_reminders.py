from django.core.management.base import BaseCommand
from django.utils import timezone
import time
from datetime import datetime, timedelta
from django.core.mail import send_mail
import pytz
from goals.models import DailyActivity  # adjust import
from notifications.models import Notification

time.sleep(10)

class Command(BaseCommand):
    help = "Send reminders for upcoming daily activities"

    def handle(self, *args, **options):
        now_utc = timezone.now()
        window = timedelta(minutes=5)  # allow slight delay tolerance

        activities = DailyActivity.objects.filter(reminder_sent=False, template__is_active=True)

        for activity in activities:
            user = activity.template.user
            if not user or not hasattr(user, "timezone"):
                continue

            user_tz = pytz.timezone(user.timezone)
            today = timezone.localdate()
            start_local = datetime.combine(today, activity.start_time)
            start_local = user_tz.localize(start_local)
            start_utc = start_local.astimezone(pytz.UTC)

            if start_utc <= now_utc <= start_utc + window:
                # Send notification
                Notification.objects.create(
                    user=user,
                    message=f"⏰ Reminder: {activity.title} is starting now!",
                    type="reminder"
                )

                # (Optional) send email
                send_mail(
                    subject=f"Reminder: {activity.title} starting soon",
                    message=f"Your activity '{activity.title}' starts now.",
                    from_email="no-reply@kommitly.com",
                    recipient_list=[user.email],
                )

                activity.reminder_sent = True
                activity.save()
                self.stdout.write(self.style.SUCCESS(f"Reminder sent for {activity.title}"))
