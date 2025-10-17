from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyActivity, DailyActivityHistory
from users.models import User
import pytz

class Command(BaseCommand):
    help = "Reset daily activities per user's timezone and archive all activities"

    def handle(self, *args, **kwargs):
        now_utc = timezone.now()
        total_reset = 0
        total_users = 0
        total_archived = 0

        self.stdout.write(self.style.SUCCESS(f"🌍 Starting per-user daily activity reset at {now_utc} UTC"))

        for user in User.objects.all():
            try:
                user_tz = pytz.timezone(user.timezone)
            except Exception:
                user_tz = pytz.UTC

            user_local_time = now_utc.astimezone(user_tz)
            user_today = user_local_time.date()

            # Activities before today
            user_activities = DailyActivity.objects.filter(template__user=user)

            if not user_activities.exists():
                continue

            # Archive all activities, keeping completed status
            for act in user_activities:
                DailyActivityHistory.objects.create(
                    activity=act,
                    date=act.date,
                    completed=act.completed,
                    completed_at=timezone.now() if act.completed else None
                )
            total_archived += user_activities.count()

            # Reset all activities for today
            updated = user_activities.update(
                completed=False,
                reminder_sent=False,
                date=user_today
            )
            total_reset += updated
            total_users += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Reset {updated} activities and archived {user_activities.count()} for {user.email or user.username} ({user.timezone})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Done! Reset {total_reset} activities for {total_users} users, archived {total_archived} activities."
            )
        )

        # Optional: log to file
        with open("/home/shanon/kommitly/kommitly_backend/daily_activity_reset.log", "a") as f:
            f.write(
                f"[{now_utc}] Reset {total_reset} activities for {total_users} users, archived {total_archived}\n"
            )
