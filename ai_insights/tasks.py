# ai_insights/tasks.py
import pytz
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from celery import shared_task
from django.utils import timezone
from users.models import User
from ai_insights.models import AIInsight
from ai_insights.utils import generate_weekly_activity_feedback  # the function you already have

@shared_task
def send_weekly_activity_reports():
    """
    Generate and email weekly AI activity reports for all active users.
    """
    now = timezone.now()
    users = User.objects.filter(is_verified=True)

    for user in users:
        try:
            insight_text = generate_weekly_activity_feedback(user)
            if not insight_text:
                continue  # skip users with no activity this week

            subject = "📈 Your Kommitly Weekly Report"
            from_email = "no-reply@kommitly.com"
            to_email = [user.email]

            context = {
                "user": user,
                "insight_text": insight_text,
                "week_range": f"{(now - timedelta(days=7)).strftime('%b %d')} - {now.strftime('%b %d, %Y')}",
                "app_link": "https://kommitly-frontend.vercel.app/dashboard/",
            }

            # Use your email template (HTML + text)
            html_content = render_to_string("email/weekly_report.html", context)
            text_content = f"Hi {user.first_name},\n\n{insight_text}\n\nVisit your dashboard for more insights."

            send_mail(
                subject,
                text_content,
                from_email,
                to_email,
                html_message=html_content
            )

            AIInsight.objects.create(user=user, insight_text=insight_text)

        except Exception as e:
            print(f"❌ Error generating weekly report for {user.email}: {e}")
