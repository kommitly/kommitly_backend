from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyTemplate, DailyActivity
from goals.constants import FIXED_ACTIVITIES


class Command(BaseCommand):
    help = "Generate new DailyActivity entries each day from active templates (including fixed activities)"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        today = now.date()

        self.stdout.write(self.style.SUCCESS(f"DEBUG: Generating daily activities for {now}"))

        templates = DailyTemplate.objects.filter(is_active=True).select_related("user")
        self.stdout.write(self.style.SUCCESS(f"Found {templates.count()} active daily templates"))

        total_created = 0
        total_skipped = 0

        for template in templates:
            username = str(template.user) if template.user else "Unknown User"

            # Skip if today's activities already exist for this template
            if DailyActivity.objects.filter(template=template, date=today).exists():
                total_skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"⏭️ Activities already exist for {username} ({today}) — skipped")
                )
                continue

            # Create fixed activities
            for fixed in FIXED_ACTIVITIES:
                DailyActivity.objects.create(
                    template=template,
                    title=fixed["title"],
                    start_time=fixed["start_time"],
                    end_time=fixed["end_time"],
                    reminder_sent=False,
                    completed=False,
                    is_fixed=True,
                    date=today,
                )
                total_created += 1

            # Create user-defined activities
            for user_activity in template.activities.filter(is_fixed=False):
                DailyActivity.objects.create(
                    template=template,
                    title=user_activity.title,
                    description=user_activity.description,
                    start_time=user_activity.start_time,
                    end_time=user_activity.end_time,
                    reminder_sent=False,
                    completed=False,
                    is_fixed=False,
                    date=today,
                )
                total_created += 1

            self.stdout.write(
                self.style.SUCCESS(f"✅ Created activities for {username} ({today})")
            )

        # Summary log
        self.stdout.write(self.style.SUCCESS(
            f"🎉 All daily activities processed — {total_created} created, {total_skipped} skipped"
        ))

        # Optional: write to cron log
        with open("/home/shanon/kommitly/kommitly_backend/cron_test_output.log", "a") as f:
            f.write(f"[{now}] Created: {total_created}, Skipped: {total_skipped}\n")
