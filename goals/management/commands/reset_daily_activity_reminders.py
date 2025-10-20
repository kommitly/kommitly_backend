from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyActivity, DailyActivityHistory
from users.models import User
import pytz

class Command(BaseCommand):
    help = "Reset daily activities per user's timezone and archive all activities safely"

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

            # Fetch only activities before today
            user_activities = DailyActivity.objects.filter(
                template__user=user,
                date__lt=user_today
            )

            if not user_activities.exists():
                continue

            archived_count = 0

            # ✅ Archive each activity only once
            for act in user_activities:
                already_archived = DailyActivityHistory.objects.filter(
                    activity=act,
                    date=act.date
                ).exists()

                if already_archived:
                    continue

                DailyActivityHistory.objects.create(
                    activity=act,
                    date=act.date,
                    completed=act.completed,
                    completed_at=timezone.now() if act.completed else None
                )
                archived_count += 1

            total_archived += archived_count

            # ✅ Only reset if activities for today haven’t already been created
            already_reset_today = DailyActivity.objects.filter(
                template__user=user,
                date=user_today
            ).exists()

            if not already_reset_today:
                updated = user_activities.update(
                    completed=False,
                    reminder_sent=False,
                    date=user_today
                )
                total_reset += updated
                total_users += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Reset {updated} activities and archived {archived_count} for {user.email or user.username} ({user.timezone})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ Skipped reset for {user.email or user.username}: already reset today."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Done! Reset {total_reset} activities for {total_users} users, archived {total_archived} activities."
            )
        )

        # ✅ Log summary to file
        # with open("/home/shanon/kommitly/kommitly_backend/daily_activity_reset.log", "a") as f:
        #     f.write(
        #         f"[{now_utc}] Reset {total_reset} activities for {total_users} users, archived {total_archived}\n"
        #     )
