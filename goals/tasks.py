from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
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
def reactivate_routines():
    now = timezone.now()
    call_command("reactivate_routines")  # run your management command
    return f"Routines reactivated at {now}"


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
            due_utc = task.due_date  # Already UTC-aware
            reminder_utc = datetime.combine(due_utc.date(), task.reminder_time).replace(tzinfo=pytz.UTC)

         
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


@shared_task
def send_subtask_reminders(subtask_id=None):
    from goals.models import SubTask  # Avoid circular imports

    current_time = timezone.now()
    subtasks = []

    if subtask_id:
        try:
            subtask = SubTask.objects.get(id=subtask_id, status='pending')
            subtasks = [subtask]
        except SubTask.DoesNotExist:
            logger.warning(f"No pending subtask found with id={subtask_id}")
            return
    else:
        subtasks = SubTask.objects.filter(status='pending', reminder_sent=False)

    for subtask in subtasks:
        try:
            user = subtask.task.user if subtask.task else None

            if not user or not user.timezone:
                logger.error(f"Subtask '{subtask.title}' has no user or timezone.")
                continue

            if not subtask.due_date or not subtask.reminder_time:
                logger.warning(f"Subtask '{subtask.title}' missing due_date or reminder_time")
                continue

            user_timezone = pytz.timezone(user.timezone)
            due_utc = subtask.due_date  # Already UTC-aware
            reminder_utc = datetime.combine(due_utc.date(), subtask.reminder_time).replace(tzinfo=pytz.UTC)

            

            if reminder_utc <= current_time <= reminder_utc + timedelta(minutes=2):
                subject = "⏰ Subtask Reminder from Kommitly"
                from_email = 'no-reply@kommitly.com'
                to = [user.email]

                context = {
                    'subtask': subtask,
                    'user': user,
                    'app_link': f"https://kommitly-frontend.vercel.app/dashboard/tasks/{subtask.task.id}/"
                }

                text_content = f"Reminder: {subtask.title} is due soon! Visit your Kommitly app to manage it."

                try:
                    html_content = render_to_string('email/task_reminder.html', context)
                except TemplateDoesNotExist as e:
                    logger.error(f"Template does not exist: {e}")
                    raise e

                msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                Notification.objects.create(
                    user=user,
                    content_type=ContentType.objects.get_for_model(subtask),
                    object_id=subtask.id,
                    message=f"⏰ Reminder: '{subtask.title}' is due soon.",
                    link=f"https://kommitly-frontend.vercel.app/dashboard/tasks/{subtask.task.id}/",
                    type="reminder"
                )

                subtask.reminder_sent = True
                subtask.save()
                logger.info(f"Reminder sent for subtask: {subtask.title} to {user.email}")

        except Exception as e:
            logger.error(f"Error sending subtask reminder: {str(e)}")





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

            due_utc = ai_task.due_date  # Already UTC-aware
            reminder_utc = datetime.combine(due_utc.date(), ai_task.reminder_time).replace(tzinfo=pytz.UTC)

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
            ai_subtask = AiSubTask.objects.get(id=subtask_id, status__in=['pending', 'overdue'])
            ai_subtasks = [ai_subtask]
        except AiSubTask.DoesNotExist:
            logger.warning(f"No pending ai task found with id={subtask_id}")
            return

    elif user_id:
        ai_subtasks = AiSubTask.objects.filter(status__in=['pending', 'overdue'], user_id=user_id)
        logger.info(f"Sending reminders for user_id: {user_id}")
        logger.debug(f"Tasks for user_id {user_id}: {ai_subtasks}")

    else:
        ai_subtasks = AiSubTask.objects.filter(status__in=['pending', 'overdue'], reminder_sent=False)

    for ai_subtask in ai_subtasks:
        try:
            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            ai_task = getattr(ai_subtask, 'ai_task', None)
            ai_goal = getattr(ai_task, 'ai_goal', None) if ai_task else None

            if not user or not ai_subtask.due_date or not ai_subtask.reminder_time:
                logger.warning(f"Skipping AI subtask '{ai_subtask.title}' missing user, due_date or reminder_time")
                continue

            # --- Reminder calculation in UTC ---
            due_utc = ai_subtask.due_date  # Already UTC-aware
            reminder_utc = datetime.combine(due_utc.date(), ai_subtask.reminder_time).replace(tzinfo=pytz.UTC)

            logger.debug(
                f"Reminder time (UTC) for ai subtask  '{ai_subtask.title}': {reminder_utc}, current time: {current_time}"
            )

            # Check 2-minute window
            if reminder_utc <= current_time <= reminder_utc + timedelta(minutes=2):
                subject = f"⏰ Upcoming Subtask Due: {ai_subtask.title}"
                from_email = 'no-reply@kommitly.com'
                to = [user.email]

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

                # ✅ In-app notification
                Notification.objects.create(
                    user=user,
                    content_type=ContentType.objects.get_for_model(ai_subtask),
                    object_id=ai_subtask.id,
                    message=f"⏰ Reminder: '{ai_subtask.title}' is due soon.",
                    link=context['app_link'],
                    type="reminder"
                )

                # Mark reminder sent
                ai_subtask.reminder_sent = True
                ai_subtask.save()
                logger.info(f"Reminder sent for task: {ai_subtask.title} to {user.email}")

        except Exception as e:
            logger.error(f"Error processing AI subtask '{ai_subtask.title}': {str(e)}")




@shared_task
def send_overdue_task_notifications(task_id=None):
    now_utc = timezone.now()

    if task_id:
        try:
            task = Task.objects.get(
                id=task_id,
                status__in=["pending", "in-progress","overdue"],
                due_date__lt=now_utc
                )
            tasks=[task]
        except Task.DoesNotExist:
            logger.warning(f"No pending task found with id={task_id}")
            return
    
    else:
        tasks = Task.objects.filter(
            status__in=["pending", "in-progress","overdue"],
            due_date__lt=now_utc
        )

    
    for task in tasks:
        
        try:
            # Set overdue status + reason
            if task.status == "pending":
                task.overdue_reason = "not_started"
            elif task.status == "in-progress":
                task.overdue_reason = "unfinished"

            task.status = "overdue"
            task.overdue_notified = True
            task.save(update_fields=["status", "overdue_reason", "overdue_notified"])

            user = task.user
           
            if not user:
                continue




  
            subject = f"⚠️ Overdue Task: {task.title}"
            from_email = "no-reply@kommitly.com"
            to = [user.email]

            context = {
                "task": task,
                "user": user,
                "app_link": f"https://kommitly-frontend.vercel.app/dashboard/tasks/{task.id}/"
            }
            text_content = f"⚠️ Your task '{task.title}' is overdue! Please review it in Kommitly."
            html_content = render_to_string("email/task_overdue.html", context)
            

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # ✅ In-app notification
            Notification.objects.create(
                user=user,
                content_type=ContentType.objects.get_for_model(task),
                object_id=task.id,
                message=f"⚠️ Overdue: '{task.title}' needs your attention .",
                link=context["app_link"],
                type="overdue"
            )

            logger.info(f"Overdue notification sent for task: {task.title} to {user_email}")

        except Exception as e:
            logger.error(f"Error sending overdue Task notification: {str(e)}")




def send_overdue_subtask_notifications(subtask_id):
    from goals.models import SubTask

    try:
        subtask = SubTask.objects.get(id=subtask_id, status__in=["pending", "in_progress"])
    except SubTask.DoesNotExist:
        return

    user = subtask.task.user if subtask.task else None
    if not user:
        return

    # --- Mark overdue ---
    if subtask.status == "pending":
        subtask.overdue_reason = "not_started"
    elif subtask.status == "in_progress":
        subtask.overdue_reason = "unfinished"

    subtask.status = "overdue"
    subtask.overdue_notified = True
    subtask.save(update_fields=["status", "overdue_reason", "overdue_notified"])

    # --- Create in-app notification ---
    Notification.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(subtask),
        object_id=subtask.id,
        message=f"⚠️ Overdue: '{subtask.title}' was due on {subtask.due_date}.",
        link=f"https://kommitly-frontend.vercel.app/dashboard/tasks/{subtask.task.id}/",
        type="overdue"
    )

    # --- Optional email ---
    subject = "⚠️ Overdue Subtask in Kommitly"
    from_email = 'no-reply@kommitly.com'
    to = [user.email]

    context = {
        'subtask': subtask,
        'user': user,
        'app_link': f"https://kommitly-frontend.vercel.app/dashboard/tasks/{subtask.task.id}/"
    }

    text_content = f"'{subtask.title}' was due on {subtask.due_date}. Please check Kommitly."

    try:
        html_content = render_to_string('email/task_overdue.html', context)
    except TemplateDoesNotExist:
        html_content = None

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    if html_content:
        msg.attach_alternative(html_content, "text/html")
    msg.send()

    logger.info(f"Overdue alert sent for subtask: {subtask.title} to {user.email}")
    
    

def send_overdue_ai_subtask_notifications(subtask_id=None):
    now_utc = timezone.now()

    if subtask_id:
        try:
            ai_subtask = AiSubTask.objects.get(
                id=subtask_id,
                status__in=["pending", "in-progress","overdue"],
                due_date__lt=now_utc
            )
            ai_subtasks = [ai_subtask]
        except AiSubTask.DoesNotExist:
            return
    else:
        ai_subtasks = AiSubTask.objects.filter(
            status__in=["pending", "in-progress","overdue"],
            due_date__lt=now_utc
        )

    for ai_subtask in ai_subtasks:
        try:
            # Set overdue status + reason
            if ai_subtask.status == "pending":
                ai_subtask.overdue_reason = "not_started"
            elif ai_subtask.status == "in-progress":
                ai_subtask.overdue_reason = "unfinished"

            ai_subtask.status = "overdue"
            ai_subtask.overdue_notified = True
            ai_subtask.save(update_fields=["status", "overdue_reason", "overdue_notified"])

            user = ai_subtask.ai_task.ai_goal.user if ai_subtask.ai_task and ai_subtask.ai_task.ai_goal else None
            ai_task = getattr(ai_subtask, "ai_task", None)
            ai_goal = getattr(ai_task, "ai_goal", None) if ai_task else None

            if not user:
                continue

            subject = f"⚠️ Overdue Subtask: {ai_subtask.title}"
            from_email = "no-reply@kommitly.com"
            to = [user.email]

            context = {
                "ai_subtask": ai_subtask,
                "ai_task": ai_task,
                "ai_goal": ai_goal,
                "user": user,
                "app_link": f"https://kommitly-frontend.vercel.app/dashboard/ai-goal/{ai_goal.id}/task/{ai_task.id}/subtask/{ai_subtask.id}"
            }
            text_content = f"Your subtask '{ai_subtask.title}' is overdue. Please review it in Kommitly."
            html_content = render_to_string("email/ai_subtask_overdue.html", context)

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # In-app notification
            Notification.objects.create(
                user=user,
                content_type=ContentType.objects.get_for_model(ai_subtask),
                object_id=ai_subtask.id,
                message=f"⚠️ Overdue: '{ai_subtask.title}' needs your attention.",
                link=context["app_link"],
                type="overdue"
            )

            logger.info(f"Overdue notification sent for AI subtask: {ai_subtask.title}")

        except Exception as e:
            logger.error(f"Error sending overdue AI subtask notification: {str(e)}")
