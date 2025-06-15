from celery import shared_task
from django.utils.timezone import now, timedelta, datetime, make_aware
from django.core.mail import send_mail
from .models import Task, AiTask, AiSubTask,AiGoal
import pytz
from django.utils import timezone
from notifications.models import Notification
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from templates import email
from django.contrib.contenttypes.models import ContentType



logger = logging.getLogger(__name__)


@shared_task
def send_task_reminders(task_id=None, user_id=None):
    current_time = timezone.now()
    tasks = []

    if task_id:
        try:
            task = Task.objects.get(id=task_id, status='pending')
            tasks = [task]
        except Task.DoesNotExist:
            logger.warning(f"No pending task found with id={task_id}")
            return

    elif user_id:
        tasks = Task.objects.filter(status='pending', user_id=user_id)
        logger.info(f"Sending reminders for user_id: {user_id}")
        logger.debug(f"Tasks for user_id {user_id}: {tasks}")

    else:
        tasks = Task.objects.filter(status='pending')

    for task in tasks:
        try:
            user = task.user or (task.goal.user if task.goal else None)

            if not user:
                logger.error(f"Task '{task.title}' has no associated user.")
                continue

            if not task.due_date or not task.reminder_time:
                logger.warning(f"Task '{task.title}' is missing due_date or reminder_time")
                continue

            user_timezone = pytz.timezone(user.timezone)
            user_email = user.email

            # Combine due date and reminder time into a datetime
            reminder_local = datetime.combine(task.due_date, task.reminder_time)

            # Localize if naive
            if timezone.is_naive(reminder_local):
                reminder_local = user_timezone.localize(reminder_local)

            reminder_utc = reminder_local.astimezone(pytz.UTC)
            logger.debug(f"Reminder time (UTC) for task '{task.title}': {reminder_utc}, current time: {current_time}")

            if reminder_utc <= current_time <= reminder_utc + timedelta(minutes=2):
                subject = "⏰ Task Reminder from Kommitly"
                from_email = 'no-reply@kommitly.com'
                to = [user_email]
                context = {
                    'task': task,
                    'user': user,
                    'app_link': f"https://kommitly-frontend.vercel.app/dashboard/tasks/{task.id}/"
                }
                text_content = f"Reminder: {task.title} is due soon! Visit your Kommitly app to manage it."
                try:
                    html_content = render_to_string('email/task_reminder.html', context)
                except TemplateDoesNotExist as e:
                    logger.error(f"Template does not exist: {e}")
                    raise e

                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                 # ✅ In-app notification
                Notification.objects.create(
                    user=user,
                    content_type=ContentType.objects.get_for_model(task),
                    object_id=task.id,
                    message=f"⏰ Reminder: '{task.title}' is due soon.",
                    link=f"https://kommitly-frontend.vercel.app/dashboard/tasks/{task.id}/",
                    type="reminder"
                )

                task.reminder_sent = True
                task.save()
                logger.info(f"Reminder sent for task: {task.title} to {user_email}")
            else:
                logger.debug(f"Not yet time to send reminder for task '{task.title}'")

        except Exception as e:
            logger.error(f"Error with task '{task.title}': {str(e)}")

"""
def send_all_task_reminders():
    current_time = now()
    tasks = Task.objects.filter(status='pending')

    for task in tasks:
        try:
            user = task.user or (task.goal.user if task.goal else None)
            if not user or not task.due_date or not task.reminder_time:
                continue

            user_email = user.email
            user_timezone = pytz.timezone(user.timezone)
            reminder_local = datetime.combine(task.due_date.date(), task.reminder_time)
            reminder_local = user_timezone.localize(reminder_local)
            reminder_utc = reminder_local.astimezone(pytz.UTC)


            logger.debug(f"[{user_email}] Task '{task.title}' → Local: {reminder_local}, UTC: {reminder_utc}")
            logger.debug(f"Comparing: Reminder UTC {reminder_utc} <= Current UTC {current_time}")


            if reminder_utc <= current_time:
                send_mail(
                    'Task Reminder',
                    f"Reminder: {task.title} is due soon!",
                    'no-reply@kommitly.com',
                    [user.email],
                )
                logger.info(f"Reminder sent for task: {task.title} to {user_email}")

        except Exception as e:
            logger.error(f"Error sending reminder for task '{task.title}': {e}")


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
"""

def send_ai_task_reminders(task_id=None, user_id=None):
    current_time = timezone.now()
    ai_tasks = []
    

    if task_id:
        try:
            ai_task = AiTask.objects.get(id=task_id, status='in-progress')
            ai_tasks = [ai_task]
        except AiTask.DoesNotExist:
            logger.warning(f"No in-progress ai task found with id={task_id}")
            return

    elif user_id:
        ai_tasks = AiTask.objects.filter(status='in-progress', user_id=user_id)
        logger.info(f"Sending reminders for user_id: {user_id}")
        logger.debug(f"Tasks for user_id {user_id}: {ai_tasks}")

    else:
        ai_tasks = AiTask.objects.filter(status='pending')

    for ai_task in ai_tasks:
        try:
            user = ai_task.ai_goal.user or (ai_task.ai_goal.user if ai_task.ai_goal else None)
            ai_goal = getattr(ai_task, 'ai_goal', None) if ai_task else None
            if not user:
                logger.error(f"Task '{ai_task.title}' has no associated user.")
                continue

            if not ai_task.due_date or not ai_task.reminder_time:
                logger.warning(f"Task '{ai_task.title}' is missing due_date or reminder_time")
                continue

            user_timezone = pytz.timezone(user.timezone)
            user_email = user.email

            # Combine due date and reminder time into a datetime
            reminder_local = datetime.combine(ai_task.due_date, ai_task.reminder_time)

            # Localize if naive
            if timezone.is_naive(reminder_local):
                reminder_local = user_timezone.localize(reminder_local)

            reminder_utc = reminder_local.astimezone(pytz.UTC)
            logger.debug(f"Reminder time (UTC) for ai task '{ai_task.title}': {reminder_utc}, current time: {current_time}")

            if reminder_utc <= current_time <= reminder_utc + timedelta(minutes=2):
                subject = "⏰ Task Reminder from Kommitly"
                from_email = 'no-reply@kommitly.com'
                to = [user_email]
                context = {
                    'task': ai_task,
                    'user': user,
                    'app_link': f"https://kommitly-frontend.vercel.app/dashboard/ai-goal/{ai_goal.id}"
                }
                text_content = f"Reminder: {ai_task.title} is due soon! Visit your Kommitly app to manage it."
                try:
                    html_content = render_to_string('email/ai_task_reminder.html', context)
                except TemplateDoesNotExist as e:
                    logger.error(f"Template does not exist: {e}")
                    raise e

                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                       # ✅ In-app notification for ai_task
                Notification.objects.create(
                    user=user,
                    content_type=ContentType.objects.get_for_model(ai_task),
                    object_id=ai_task.id,
                    message=f"⏰ Reminder: '{ai_task.title}' is due soon.",
                    link=f"https://kommitly-frontend.vercel.app/dashboard/ai-goal/{ai_goal.id}",
                    type="reminder"
                )



                ai_task.reminder_sent = True
                ai_task.save()
                logger.info(f"Reminder sent for task: {ai_task.title} to {user_email}")
            else:
                logger.debug(f"Not yet time to send reminder for task '{ai_task.title}'")

        except Exception as e:
            logger.error(f"Error with task '{ai_task.title}': {str(e)}")



def send_ai_subtask_reminders(subtask_id=None, user_id=None):
    current_time = timezone.now()
    ai_subtasks = []
    

    if subtask_id:
        try:
            ai_subtask = AiSubTask.objects.get(id=subtask_id, status='pending')
            ai_subtasks = [ai_subtask]
        except AiSubTask.DoesNotExist:
            logger.warning(f"No pending ai task found with id={subtask_id}")
            return

    elif user_id:
        ai_subtasks = AiSubTask.objects.filter(status='pending', user_id=user_id)
        logger.info(f"Sending reminders for user_id: {user_id}")
        logger.debug(f"Tasks for user_id {user_id}: {ai_subtasks}")

    else:
        ai_subtasks = AiSubTask.objects.filter(status='pending', reminder_sent=False)

    for ai_subtask in ai_subtasks:
        try:
            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            ai_task = getattr(ai_subtask, 'ai_task', None)
            ai_goal = getattr(ai_task, 'ai_goal', None) if ai_task else None

            logger.debug(f"Processing AI subtask: {ai_subtask.title}, AI task: {ai_task.title if ai_task else 'N/A'}, AI goal: {ai_goal.title if ai_goal else 'N/A'}")



            if not user:
                logger.error(f"Task '{ai_subtask.title}' has no associated user.")
                continue

            if not ai_subtask.due_date or not ai_subtask.reminder_time:
                logger.warning(f"Task '{ai_subtask.title}' is missing due_date or reminder_time")
                continue

            user_timezone = pytz.timezone(user.timezone)
            user_email = user.email

            # Combine due date and reminder time into a datetime
            reminder_local =  datetime.combine(
                    ai_subtask.due_date.date(),
                    ai_subtask.reminder_time
                )

            # Localize if naive
            if timezone.is_naive(reminder_local):
                reminder_local = user_timezone.localize(reminder_local)

            reminder_utc = reminder_local.astimezone(pytz.UTC)
            logger.debug(f"Reminder time (UTC) for ai task '{ai_subtask.title}': {reminder_utc}, current time: {current_time}")

            if reminder_utc <= current_time <= reminder_utc + timedelta(minutes=2):
                subject = "⏰ Upcoming Subtask Due: "f"{ai_subtask.title}"
                from_email = 'no-reply@kommitly.com'
                to = [user_email]
                context = {
                    'ai_subtask': ai_subtask,
                    'ai_task': ai_task,
                    'ai_goal': ai_goal,
                    'user': user,
                    'app_link': f"https://kommitly-frontend.vercel.app/dashboard/ai-goal/{ai_goal.id}/task/{ai_task.id}/subtask/{ai_subtask.id}"
                }
                text_content = f"Reminder: {ai_subtask.title} is due soon! Visit your Kommitly app to manage it."
                try:
                    html_content = render_to_string('email/ai_subtask_reminder.html', context)
                except TemplateDoesNotExist as e:
                    logger.error(f"Template does not exist: {e}")
                    raise e

                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                          # ✅ In-app notification for ai_subtask
                Notification.objects.create(
                    user=user,
                    content_type=ContentType.objects.get_for_model(ai_subtask),
                    object_id=ai_subtask.id,
                    message=f"⏰ Reminder: '{ai_subtask.title}' is due soon.",
                    link=f"https://kommitly-frontend.vercel.app/dashboard/ai-goal/{ai_goal.id}/task/{ai_task.id}/subtask/{ai_subtask.id}",
                    type="reminder"
                )


                ai_subtask.reminder_sent = True
                ai_subtask.save()
                logger.info(f"Reminder sent for task: {ai_subtask.title} to {user_email}")
            else:
                logger.debug(f"Not yet time to send reminder for task '{ai_subtask.title}'")

        except Exception as e:
            logger.error(f"Error with task '{ai_subtask.title}': {str(e)}")
