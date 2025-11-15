import pytz
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from celery import shared_task
from django.utils import timezone
from users.models import User
from ai_insights.models import AIInsight
from ai_insights.utils import generate_weekly_activity_feedback
from goals.models import Goal, AiGoal

@shared_task
def send_weekly_activity_reports():
    """
    1. Automatically marks goals as 'abandoned' if untouched for 7 days.
    2. Generates and emails weekly activity reports for active users, OR
       sends re-engagement emails showing abandoned goals for inactive users.
    """
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7) 
    
    # ------------------------------------------------------------------
    # 1. AUTOMATIC GOAL ABANDONMENT (7-day threshold)
    # ------------------------------------------------------------------
    
    # Update Goal model
    abandoned_goals_count = Goal.objects.filter(
        status='active',
        progress__lt=100,
        updated_at__lt=seven_days_ago
    ).update(status='abandoned')
    print(f"DEBUG: Marked {abandoned_goals_count} Goal objects as 'abandoned'.")

    # Update AiGoal model
    abandoned_aigoals_count = AiGoal.objects.filter(
        status='active',
        progress__lt=100,
        updated_at__lt=seven_days_ago
    ).update(status='abandoned')
    print(f"DEBUG: Marked {abandoned_aigoals_count} AiGoal objects as 'abandoned'.")
    
    # ------------------------------------------------------------------
    # 2. EMAIL REPORT GENERATION
    # ------------------------------------------------------------------
    users = User.objects.filter(is_verified=True)
    from_email = "no-reply@kommitly.com"

    for user in users:
        try:
            insight_text = generate_weekly_activity_feedback(user)
            to_email = [user.email]

            # --- A. ACTIVE USER LOGIC (Insight text is available) ---
            if insight_text:
                subject = "📈 Your Kommitly Weekly Report"

                context = {
                    "user": user,
                    "insight_text": insight_text,
                    "week_range": f"{(now - timedelta(days=7)).strftime('%b %d')} - {now.strftime('%b %d, %Y')}",
                    "app_link": "https://kommitly-frontend.vercel.app/dashboard/",
                }

                # Use your email template (HTML + text)
                html_content = render_to_string("email/weekly_report.html", context)
                text_content = f"Hi {user.first_name},\n\n{insight_text}\n\nVisit your dashboard for more insights."

                # Send Active Report: Uses html_content for rich email display
                send_mail(subject, text_content, from_email, to_email, html_message=html_content)

                AIInsight.objects.create(user=user, insight_text=insight_text)
                
                # Logging for active users
                print(f"--- SENT ACTIVE REPORT to {user.email} ---")

            # --- B. INACTIVE USER LOGIC (No activity log this week) ---
            else:
                # 1. Retrieve all abandoned goals for the user (up to 4 total)
                abandoned_goals = list(Goal.objects.filter(
                    user=user, 
                    status='abandoned'
                ).order_by('-updated_at')[:2]) 
                
                abandoned_goals += list(AiGoal.objects.filter(
                    user=user, 
                    status='abandoned'
                ).order_by('-updated_at')[:2]) 

                goals_to_show = abandoned_goals[:4]
                
                re_engagement_subject = "👋 We Missed You! Time to Get Started?"

                re_engagement_context = {
                    "user": user,
                    "app_link": "https://kommitly-frontend.vercel.app/dashboard/",
                    "abandoned_goals": goals_to_show,
                }

                # Use the specific template for re-engagement
                html_content_inactive = render_to_string("email/re_engagement.html", re_engagement_context)
                
                if goals_to_show:
                    goal_titles = [g.title for g in goals_to_show]
                    text_content_inactive = (
                        f"Hi {user.first_name},\n\n"
                        "We noticed you haven't logged any activity this past week. "
                        f"It looks like you left these goals unfinished:\n - {'\n - '.join(goal_titles)}\n\n"
                        "Ready to jump back in? Click the link below to continue your journey!"
                    )
                else:
                    text_content_inactive = (
                        f"Hi {user.first_name},\n\n"
                        "We noticed you haven't logged any activity this past week. "
                        "We'd love to help you reach your next milestone. Click the link below to get started!"
                    )
                
                # Send Re-engagement Email: Uses html_content_inactive for rich email display
                send_mail(re_engagement_subject, text_content_inactive, from_email, to_email, html_message=html_content_inactive)
                print(f"--- SENT RE-ENGAGEMENT EMAIL to {user.email} ---")
                
        except Exception as e:
            print(f"❌ Error processing report/email for {user.email}: {e}")