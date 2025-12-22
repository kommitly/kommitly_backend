import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from templates import email
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)

def send_verification_email(user):
    logger.debug(f"Sending verification email to: {user}")

    """
    Sends a verification email to a newly registered user.
    """
    verification_link = f"https://kommitly-backend.onrender.com/api/verify/{user.verification_token}/"
    subject = "Verify your Kommitly Account"
    from_email = "no-reply@kommitly.com"
    to = [user.email]

    context = {
        "user": user,
        "verification_link": verification_link,
    }

    text_content = f"Hi {user.first_name}, please verify your account: {verification_link}"
    html_content = render_to_string("email/verify-email.html", context)

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        user.email_sent = True
        user.save(update_fields=['email_sent'])
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False