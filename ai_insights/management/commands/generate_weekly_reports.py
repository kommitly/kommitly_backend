from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from users.models import UserActivity
from ai_insights.tasks import send_weekly_activity_reports


class Command(BaseCommand):
    help = "Generate and email weekly activity reports to users."

    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting weekly report generation...")
        send_weekly_activity_reports()  # async task
        self.stdout.write(self.style.SUCCESS("✅ Weekly activity report task dispatched."))
