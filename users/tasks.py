from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_verification_email(user_id, first_name, email, verification_link):
    subject = "Verify your Kommitly Account"
    message = f"Hi {first_name},\n\nClick the link below to verify your account:\n{verification_link}"
    send_mail(subject, message, "no-reply@kommitly.com", [email])
