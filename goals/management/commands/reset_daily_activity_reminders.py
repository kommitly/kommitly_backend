from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyTemplate, DailyActivity
from goals.constants import FIXED_ACTIVITIES  # import your constants

class Command(BaseCommand):
    help = "Generate new DailyActivity entries each day from active templates (including fixed activities)"

    def handle(self, *args, **options):
        today = timezone.localdate()
        templates = DailyTemplate.objects.filter(is_active=True)

        for template in templates:
            # Avoid duplicates for the same day
            if DailyActivity.objects.filter(template=template, date=today).exists():
                continue

            # 1️⃣ Add fixed (default) activities
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

            # 2️⃣ Add user-defined activities (optional)
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

            self.stdout.write(
                self.style.SUCCESS(f"✅ Created activities for {template.user.username} ({today})")
            )
