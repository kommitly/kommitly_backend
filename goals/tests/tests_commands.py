from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from datetime import time, timedelta, datetime
from goals.models import Routine, Task, SubTask, AiSubTask

class ReactivateRoutinesTest(TestCase):
    def setUp(self):
        today = timezone.now().date()

        # Routine that should trigger daily
        self.routine = Routine.objects.create(
            title="Daily Routine",
            is_active=True,
            start_date=today,
            frequency="daily",
            time_of_day=time(18, 0),
            reminder_time=time(16, 50)
        )

        # Add tasks/subtasks/ai_subtasks
        self.task = Task.objects.create(
            title="Task 1",
            routine=self.routine,
            status="completed",
            completed_at=timezone.now(),
            due_date=timezone.now(),
        )

        self.subtask = SubTask.objects.create(
            title="SubTask 1",
            task=self.task,
            routine=self.routine,
            status="completed",
            completed_at=timezone.now(),
            due_date=timezone.now(),
        )

        self.ai_subtask = AiSubTask.objects.create(
            title="AiSubTask 1",
            ai_task=None,  # or a related object if required
            routine=self.routine,
            status="completed",
            completed_at=timezone.now(),
            due_date=timezone.now(),
        )

    def test_reactivation_command(self):
        # Run the management command
        call_command("reactivate_routines")  # name of your command file

        # Refresh from DB
        self.task.refresh_from_db()
        self.subtask.refresh_from_db()
        self.ai_subtask.refresh_from_db()

        # Assertions
        self.assertEqual(self.task.status, "pending")
        self.assertIsNone(self.task.completed_at)
        self.assertEqual(self.subtask.status, "pending")
        self.assertIsNone(self.subtask.completed_at)
        self.assertEqual(self.ai_subtask.status, "pending")
        self.assertIsNone(self.ai_subtask.completed_at)
