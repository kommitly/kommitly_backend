from django.core.management.base import BaseCommand
from django.utils import timezone
from goals.models import DailyActivity

class Command(BaseCommand):
    help = "Reset reminder_sent flag for daily activities"

    def handle(self, *args, **options):
        DailyActivity.objects.update(reminder_sent=False)
        self.stdout.write(self.style.SUCCESS("Daily activity reminders reset"))
