from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
import pytz, time

from goals.models import DailyActivity
from notifications.models import Notification


class Command(BaseCommand):
    help = "Send reminders for upcoming daily activities"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting daily activity reminder check..."))
        
        window_minutes = 5
        
        now_utc = timezone.now()
        past_utc = now_utc - timedelta(minutes=window_minutes)
        
        # --- OPTIMIZED QUERY FOR TODAY'S ACTIVITIES ---
        # 1. Fetch activities for the current UTC date. This significantly reduces the initial data set.
        #    The final check against the user's local date is still needed, but this is a huge performance boost.
        activities = DailyActivity.objects.filter(
            reminder_sent=False,
            template__is_active=True,
            completed=False,
            # Filter activities whose date is today in UTC
            # (Note: This is an approximation since dates are user-local, but it's a fast filter)
            date=now_utc.date() 
        ).select_related("template", "template__user")

        self.stdout.write(self.style.NOTICE(f"Fetched {activities.count()} potential activities based on UTC date. {now_utc}"))

        for activity in activities:
            user = activity.template.user
            if not user or not hasattr(user, "timezone"):
                self.stdout.write(self.style.WARNING(f"Skipping Activity {activity.id}: No user or timezone."))
                continue

            # ✅ convert to user timezone
            try:
                user_tz = pytz.timezone(user.timezone)
            except Exception:
                user_tz = pytz.UTC

            user_local_now = now_utc.astimezone(user_tz)
            user_today = user_local_now.date()

            # --- LOGGING THE CHECK ---
            self.stdout.write(
                f"Checking {activity.title} (ID:{activity.id}) for user {user.email} at {now_utc}: "
                f"Activity Date={activity.date}, User Local Date={user_today}"
            )

            # ✅ only process activities whose date matches user’s local today
            if activity.date != user_today:
                self.stdout.write(self.style.WARNING(f"Activity {activity.id} skipped: Date mismatch."))
                continue

            start_local = datetime.combine(user_today, activity.start_time)
            start_local = user_tz.localize(start_local)
            start_utc = start_local.astimezone(pytz.UTC)

            # ✅ check if it's within the reminder window
            if past_utc <= start_utc <= now_utc:
                self.stdout.write(self.style.SUCCESS(f"--- MATCH: Sending reminder for {activity.title} ---"))
                message = f"⏰ Reminder: {activity.title} is starting now!"

                link = None
                linked_object = None

                # ... (rest of your link creation logic remains the same) ...
              
                if activity.task:
                    linked_object = activity.task
                    link = f"https://kommitly-frontend.vercel.app/dashboard/tasks/{activity.task.id}/"
                elif activity.subtask and activity.subtask.task:
                    linked_object = activity.subtask
                    link = f"https://kommitly-frontend.vercel.app/dashboard/tasks/{activity.subtask.task.id}/"
                elif activity.ai_subtask:
                    linked_object = activity.ai_subtask
                    ai_task = activity.ai_subtask.ai_task
                    ai_goal = getattr(ai_task, "goal", None)
                    if ai_goal:
                        link = (
                            f"https://kommitly-frontend.vercel.app/dashboard/"
                            f"ai-goal/{ai_goal.id}/task/{ai_task.id}/subtask/{activity.ai_subtask.id}"
                        )

                elif activity.template:
                    link = f"https://kommitly-frontend.vercel.app/dashboard/templates/{activity.template.id}/"


                notification_data = {
                    "user": user,
                    "message": message,
                    "type": "template-reminder",
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

                self.stdout.write(self.style.SUCCESS(f"Reminder successfully processed for {activity.title}"))
            else:
                 self.stdout.write(f"Activity {activity.id} skipped: Not yet in reminder window or already past.")

        self.stdout.write(self.style.NOTICE("Daily activity reminder check complete."))