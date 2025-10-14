from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyTemplate, DailyActivity
from goals.constants import FIXED_ACTIVITIES  # import your constants


class Command(BaseCommand):
    help = "Generate new DailyActivity entries each day from active templates (including fixed activities)"

    def handle(self, *args, **kwargs):
        now = timezone.now()  # current time in UTC
        today = now.date()
        self.stdout.write(self.style.SUCCESS(f"DEBUG: Generating daily activities for {today}"))

        # Get all active templates
        templates = DailyTemplate.objects.filter(is_active=True)
        self.stdout.write(self.style.SUCCESS(f"Found {templates.count()} active daily templates"))

        for template in templates:
            # Skip if activities for today already exist
            if DailyActivity.objects.filter(template=template, date=today).exists():
                self.stdout.write(self.style.SUCCESS(
                    f"Activities already exist for {template.user.username} ({today})"
                ))
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

            self.stdout.write(self.style.SUCCESS(
                f"✅ Created activities for {template.user.username} ({today})"
            ))
