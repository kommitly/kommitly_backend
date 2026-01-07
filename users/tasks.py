import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from templates import email
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)


def send_verification_email(user):
    # 1. Determine context based on the state of the user
    if user.pending_email:
        recipient = user.pending_email
        template = "email/change-email-verify.html"
        subject = "Confirm your new Kommitly email address"
        url_path = "verify-email"
    else:
        recipient = user.email
        template = "email/verify-email.html"
        subject = "Verify your Kommitly Account"
        url_path = "verify"

    verification_link = (
        f"https://kommitly-backend.onrender.com/api/{url_path}/{user.verification_token}/"
    )
    
    from_email = "no-reply@kommitly.com"
    to = [recipient]

    context = {
        "user": user,
        "verification_link": verification_link,
    }

    # 2. Prepare content
    text_content = f"Hi {user.first_name}, please verify your account: {verification_link}"
    
    try:
        html_content = render_to_string(template, context)
        
        # 3. Create and send the email
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # 4. Update user record
        user.email_sent = True
        user.token_created_at = timezone.now() 
        user.save(update_fields=["email_sent", "token_created_at"])

        logger.info(f"Verification email sent to {recipient}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        return False