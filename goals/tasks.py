from celery import shared_task
from django.utils.timezone import now, timedelta, datetime, make_aware
from django.core.mail import send_mail
from .models import Task, AiTask
import pytz
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_task_reminders():
    current_time = now()
    tasks = Task.objects.filter(status='pending')  # Get all pending tasks

    for task in tasks:
        if task.reminder_time:
            if task.user:
                user_timezone = pytz.timezone(task.user.timezone)
                user_email = task.user.email
            elif task.goal and task.goal.user:
                user_timezone = pytz.timezone(task.goal.user.timezone)
                user_email = task.goal.user.email
            else:
                logger.error(f"Task '{task.title}' does not have an associated user.")
                continue

            reminder_datetime = datetime.combine(task.due_date.date(), task.reminder_time)
            reminder_datetime = make_aware(reminder_datetime, pytz.UTC)  # Ensure reminder_datetime is in UTC
            logger.debug(f"Reminder datetime for task '{task.title}': {reminder_datetime}")
            if reminder_datetime <= current_time:
                send_mail(
                    'Task Reminder',
                    f"Reminder: {task.title} is due soon!",
                    'no-reply@kommitly.com',  # Replace with your actual sender email
                    [user_email],
                )
                logger.info(f"Reminder sent for task: {task.title} to {user_email}")

@shared_task
def send_ai_task_reminders():
    current_time = now()
    ai_tasks = AiTask.objects.filter(status='pending')  # Get all pending AI tasks

    for ai_task in ai_tasks:
        if ai_task.reminder_time:
            if ai_task.ai_goal and ai_task.ai_goal.user:
                user_timezone = pytz.timezone(ai_task.ai_goal.user.timezone)
                user_email = ai_task.ai_goal.user.email
            elif ai_task.user:
                user_timezone = pytz.timezone(ai_task.user.timezone)
                user_email = ai_task.user.email
            else:
                logger.error(f"AI Task '{ai_task.title}' does not have an associated AI goal or user.")
                continue

            reminder_datetime = datetime.combine(ai_task.due_date.date(), ai_task.reminder_time)
            reminder_datetime = make_aware(reminder_datetime, pytz.UTC)  # Ensure reminder_datetime is in UTC
            logger.debug(f"Reminder datetime for AI task '{ai_task.title}': {reminder_datetime}")
            if reminder_datetime <= current_time:
                send_mail(
                    'AI Task Reminder',
                    f"Reminder: {ai_task.title} is due soon!",
                    'no-reply@kommitly.com',  # Replace with your actual sender email
                    [user_email],
                )
                logger.info(f"Reminder sent for AI task: {ai_task.title} to {user_email}")