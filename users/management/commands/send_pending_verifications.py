from django.core.management.base import BaseCommand
from users.models import User
from users.tasks import send_verification_email
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Send verification emails for users who haven't received them yet"

    def handle(self, *args, **options):
        unverified_users = User.objects.filter(is_verified=False)
        for user in unverified_users:
            send_verification_email(user)
        logger.info("Verification email job completed.")
