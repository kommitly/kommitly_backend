from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification

class Command(BaseCommand):
    help = "Clean up old notifications (older than 30 days)"

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(days=30)
        deleted_count, _ = Notification.objects.filter(created_at__lt=threshold).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} old notifications"))
