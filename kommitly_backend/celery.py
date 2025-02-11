from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kommitly_backend.settings')

app = Celery('kommitly_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-task-reminders': {
        'task': 'goals.tasks.send_task_reminders',
        'schedule': crontab(minute='*'),  # Run every minute
    },
    'send-ai-task-reminders': {
        'task': 'goals.tasks.send_ai_task_reminders',
        'schedule': crontab(minute='*'),  # Run every minute
    },
}