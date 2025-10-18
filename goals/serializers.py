from rest_framework import serializers
from .models import Goal, Task, AiGoal, AiTask, SubTask, AiSubTask, Routine, DailyTemplate, DailyActivity, DailyActivityHistory
from users.models import User
from django.utils import timezone

from django.utils.timezone import make_aware, datetime
import pytz
import logging
from ai_insights.utils import get_insights
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from .timezone import get_timezone
from rest_framework import serializers
from .models import Task  # Adjust the import based on your project structure
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)



class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubTask
        fields = [
            "id", "task", "title", "description", "due_date", "status",
            "overdue_reason", "completed_at", "reminder_time", "reminder_sent",
            "last_updated", "ai_answer", "routine", "created_at"
        ]

    # ---------------------------
    # USER TIMEZONE RESOLUTION
    # ---------------------------
    def get_user_timezone(self, obj=None):
        user_tz = None
        if obj and getattr(obj, "task", None) and getattr(obj.task, "user", None):
            user = obj.task.user
            if getattr(user, "timezone", None):
                user_tz = user.timezone
                print(f"DEBUG: Found user timezone from SubTask.task.user → {user_tz}")
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            print(f"DEBUG: Using pytz timezone object → {tz}")
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    # ---------------------------
    # VALIDATION
    # ---------------------------
    def validate(self, data):
        request = self.context.get("request")
        raw_due = request.data.get("due_date") if request else None
        dt_to_process = None

        if isinstance(raw_due, str):
            dt_to_process = parse_datetime(raw_due)
            if dt_to_process is None:
                raise serializers.ValidationError({"due_date": "Invalid datetime format."})
        elif "due_date" in data:
            dt_to_process = data["due_date"]

        if dt_to_process is None:
            return data

        # --- Force naive if input is aware ---
        if timezone.is_aware(dt_to_process):
            dt_to_process = timezone.make_naive(dt_to_process, pytz.UTC)
            print(f"DEBUG: **FIX APPLIED**: Forced input to naive → {dt_to_process}")

        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        # --- Convert naive to aware using localize and normalize ---
        if timezone.is_naive(dt_to_process):
            aware_dt = user_tz.localize(dt_to_process, is_dst=None)
            aware_dt = user_tz.normalize(aware_dt)
            print(f"DEBUG: Naive input, localized to user → {aware_dt}")
        else:
            aware_dt = dt_to_process
            print(f"DEBUG: Already aware input → {aware_dt}")

        # --- Store in UTC ---
        data["due_date"] = aware_dt.astimezone(pytz.UTC)
        print(f"DEBUG: Final due_date (UTC) → {data['due_date']}")

        # --- Convert reminder_time if provided ---
        reminder_time = data.get("reminder_time")
        if reminder_time:
            if isinstance(reminder_time, str):
                try:
                    h, m, s = map(int, reminder_time.split(":"))
                    reminder_time = time(h, m, s)
                except Exception:
                    raise serializers.ValidationError({"reminder_time": "Invalid time format. Use HH:MM:SS."})

            local_due_date = data["due_date"].astimezone(user_tz).date()
            reminder_dt_local = user_tz.localize(datetime.combine(local_due_date, reminder_time), is_dst=None)
            reminder_dt_utc = reminder_dt_local.astimezone(pytz.UTC)
            data["reminder_time"] = reminder_dt_utc.time()
            print(f"DEBUG: Final reminder_time (UTC component) → {data['reminder_time']}")

        return data

    # ---------------------------
    # UPDATE LOGIC
    # ---------------------------
    def update(self, instance, validated_data):
        old_due_date = instance.due_date
        new_due_date = validated_data.get("due_date", old_due_date)
        user_tz = self.get_user_timezone(instance)

        # Proceed with normal update
        instance = super().update(instance, validated_data)

        # ✅ Reset overdue status if due date moved to the future
        now_utc = timezone.now()
        if instance.status == "overdue" and new_due_date > now_utc:
            instance.status = "pending"
            instance.overdue_reason = None
            instance.save(update_fields=["status", "overdue_reason"])
            print(f"DEBUG: SubTask {instance.id} status reset to 'pending' (new due_date is in the future)")

        # ✅ Set default reminder_time if not changed or now invalid
        if "reminder_time" not in validated_data:
            default_reminder_dt = new_due_date - timedelta(minutes=15)
            instance.reminder_time = default_reminder_dt.time()
            instance.reminder_sent = False
            instance.save(update_fields=["reminder_time", "reminder_sent"])
            print(f"DEBUG: Default reminder set to 15 minutes before due_date → {instance.reminder_time}")

        else:
            # Ensure reminder is still before due_date
            reminder_dt = datetime.combine(new_due_date.date(), instance.reminder_time)
            if reminder_dt >= new_due_date:
                default_reminder_dt = new_due_date - timedelta(minutes=15)
                instance.reminder_time = default_reminder_dt.time()
                instance.save(update_fields=["reminder_time"])
                print(f"DEBUG: Reminder adjusted to 15 minutes before due_date → {instance.reminder_time}")

        return instance

    # ---------------------------
    # TO REPRESENTATION
    # ---------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class AiSubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiSubTask
        fields = "__all__"
        read_only_fields = ["ai_task"]

    # ---------------------------
    # CREATE / UPDATE
    # ---------------------------
    def create(self, validated_data):
        ai_task_id = self.context.get("ai_task_id")
        if ai_task_id:
            validated_data["ai_task_id"] = ai_task_id
        validated_data = self._apply_due_date_status(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_due_date_status(validated_data, instance)
        instance = super().update(instance, validated_data)

        user_tz = self.get_user_timezone(instance)
        new_due_date = validated_data.get("due_date", instance.due_date)
        now_utc = timezone.now()

        # ✅ Reset overdue status if due_date moved to future
        if instance.status == "overdue" and new_due_date > now_utc:
            instance.status = "pending"
            instance.overdue_reason = None
            instance.save(update_fields=["status", "overdue_reason"])
            print(f"DEBUG: AiSubTask {instance.id} status reset to 'pending' (new due_date is in the future)")

        # ✅ If reminder_time was updated, reset reminder_sent
        if "reminder_time" in validated_data:
            instance.reminder_sent = False
            instance.save(update_fields=["reminder_sent"])
            print(f"DEBUG: Reminder time updated — reminder_sent reset to False")
        
        # ✅ Set default reminder_time if not changed
        if "reminder_time" not in validated_data:
            default_reminder_dt = new_due_date - timedelta(minutes=15)
            instance.reminder_time = default_reminder_dt.time()
            instance.reminder_sent = False
            instance.save(update_fields=["reminder_time", "reminder_sent"])
            print(f"DEBUG: Default reminder set to 15 minutes before due_date → {instance.reminder_time}")

        else:
            # Ensure reminder is still before due_date
            reminder_dt = datetime.combine(new_due_date.date(), instance.reminder_time)

            # ✅ Make reminder_dt timezone-aware (UTC)
            if timezone.is_naive(reminder_dt):
                reminder_dt = timezone.make_aware(reminder_dt, timezone=pytz.UTC)

            if reminder_dt >= new_due_date:
                default_reminder_dt = new_due_date - timedelta(minutes=15)
                instance.reminder_time = default_reminder_dt.time()
                instance.save(update_fields=["reminder_time"])
                print(f"DEBUG: Reminder adjusted to 15 minutes before due_date → {instance.reminder_time}")

        return instance

    # ---------------------------
    # APPLY DUE DATE STATUS
    # ---------------------------
    def _apply_due_date_status(self, validated_data, instance=None):
        now = timezone.now()
        due_date = validated_data.get("due_date", getattr(instance, "due_date", None))
        status = validated_data.get("status", getattr(instance, "status", None))

        if status != "completed" and due_date:
            if due_date <= now:
                validated_data["status"] = "overdue"
                if not validated_data.get("overdue_reason") and getattr(instance, "overdue_reason", None) is None:
                    validated_data["overdue_reason"] = "not_started"
            else:
                if status == "overdue":
                    validated_data["status"] = "pending"
                    validated_data["reminder_sent"] = False
                    validated_data["overdue_reason"] = None
                    validated_data["overdue_notified"] = False
        return validated_data

    # ---------------------------
    # USER TIMEZONE RESOLUTION
    # ---------------------------
    def get_user_timezone(self, obj=None):
        user_tz = None
        if obj and getattr(obj, "ai_task", None) and getattr(obj.ai_task, "ai_goal", None):
            user = getattr(obj.ai_task.ai_goal, "user", None)
            if user and getattr(user, "timezone", None):
                user_tz = user.timezone
                print(f"DEBUG: Found user timezone from AiTask.ai_goal.user → {user_tz}")
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            print(f"DEBUG: Using pytz timezone object → {tz}")
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    # ---------------------------
    # VALIDATION
    # ---------------------------
    def validate(self, data):
        request = self.context.get("request")
        raw_due = request.data.get("due_date") if request else None
        dt_to_process = None

        if isinstance(raw_due, str):
            dt_to_process = parse_datetime(raw_due)
            if dt_to_process is None:
                raise serializers.ValidationError({"due_date": "Invalid datetime format."})
        elif "due_date" in data:
            dt_to_process = data["due_date"]

        



        # --- Reminder conversion should happen regardless of due_date ---
        reminder_time = data.get("reminder_time")

        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        # ✅ If due_date is provided, handle timezone conversion as before
        if dt_to_process is not None:
            if timezone.is_aware(dt_to_process):
                dt_to_process = timezone.make_naive(dt_to_process, pytz.UTC)
            if timezone.is_naive(dt_to_process):
                aware_dt = user_tz.localize(dt_to_process, is_dst=None)
                aware_dt = user_tz.normalize(aware_dt)
            else:
                aware_dt = dt_to_process

            data["due_date"] = aware_dt.astimezone(pytz.UTC)
            print(f"DEBUG: Final due_date (UTC) → {data['due_date']}")



        
        if reminder_time:
            if isinstance(reminder_time, str):
                try:
                    h, m, s = map(int, reminder_time.split(":"))
                    reminder_time = time(h, m, s)
                except Exception:
                    raise serializers.ValidationError({"reminder_time": "Invalid time format. Use HH:MM:SS."})

            base_due_date = data.get("due_date") or getattr(self.instance, "due_date", None)
            if base_due_date:
                local_due_date = base_due_date.astimezone(user_tz).date()
                reminder_dt_local = user_tz.localize(datetime.combine(local_due_date, reminder_time), is_dst=None)
                reminder_dt_utc = reminder_dt_local.astimezone(pytz.UTC)
                data["reminder_time"] = reminder_dt_utc.time()
                print(f"DEBUG: Final reminder_time (UTC component) → {data['reminder_time']}")


        return data

    # ---------------------------
    # TO REPRESENTATION
    # ---------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data





class CreateAiTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiTask
        fields = [
            'ai_goal',
          
            'title',
       
            'description',
            'due_date',
            'status',
            'overdue_reason',
            'completed_at',
            'task_timeline',
            'reminder_time', ]

    def to_internal_value(self, data):
        if data.get('ai_goal') == 0:
            data['ai_goal'] = None
        return super().to_internal_value(data)

    
    def validate(self, data):
        due = data.get('due_date')

        if due:
            # Parse string if necessary
            if isinstance(due, str):
                due = parse_datetime(due)

            if due:
                data['reminder_time'] = (due - timedelta(minutes=30)).time()

        # Optional: prevent changing status backward
        if self.instance:
            if self.instance.status == 'completed' and data.get('status') != 'completed':
                raise serializers.ValidationError("Cannot move a completed task back to another status.")

        return data

    def create(self, validated_data):
        ai_task = AiTask.objects.create(**validated_data)
        return ai_task


class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'goal', 
            'title',
            'description',
            'due_date',
            'status',
            'overdue_reason',
            'subtasks',
            'task_timeline',
            'reminder_time',
            'tag',
            'created_at'
    
         
           ]
        extra_kwargs = {
            'goal': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True},
            'due_date': {'required': False, 'allow_null': True},
            'status': {'required': False, 'allow_null': True},
            'subtasks': {'required': False},
            'overdue_reason': {'required': False, 'allow_null': True},
            'task_timeline': {'required': False, 'allow_null': True},
            'reminder_time': {'required': False, 'allow_null': True},
            'tag': {'required': False, 'allow_null': True},
        }

    def to_internal_value(self, data):
        if data.get('goal') == 0:
            data['goal'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        due_date = data.get('due_date')
        if due_date and 'reminder_time' not in data:
            data['reminder_time'] = (due_date - timedelta(minutes=30)).time()
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        user_timezone = pytz.timezone(user.timezone) if user and user.timezone else pytz.UTC

        due_date = validated_data.get('due_date')
        reminder_time = validated_data.get('reminder_time')

        if due_date and reminder_time:
            reminder_datetime = datetime.combine(due_date.date(), reminder_time)
            reminder_datetime = make_aware(reminder_datetime, user_timezone)
            validated_data['due_date'] = reminder_datetime.astimezone(pytz.UTC)
            validated_data['reminder_time'] = reminder_datetime.astimezone(pytz.UTC).time()

        task = Task.objects.create(user=user, **validated_data)
        return task


class TaskSerializer(serializers.ModelSerializer):
    subtasks = SubTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "goal", "user", "title", "description", "due_date", "status",
            "completed_at", "subtasks", "overdue_reason", "task_timeline",
            "reminder_time", "last_updated", "reminder_sent", "tag",
            "ai_answer", "routine", "created_at","overdue_notified"
        ]

    # ---------------------------
    # USER TIMEZONE RESOLUTION
    # ---------------------------
    def get_user_timezone(self, obj=None):
        user_tz = None
        if obj and getattr(obj, "user", None) and getattr(obj.user, "timezone", None):
            user_tz = obj.user.timezone
            print(f"DEBUG: Found user timezone from Task.user → {user_tz}")
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            print(f"DEBUG: Using pytz timezone object → {tz}")
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    # ---------------------------
    # VALIDATION
    # ---------------------------
    def validate(self, data):
        request = self.context.get("request")
        raw_due = request.data.get("due_date") if request else None
        dt_to_process = None

        if isinstance(raw_due, str):
            dt_to_process = parse_datetime(raw_due)
            if dt_to_process is None:
                raise serializers.ValidationError({"due_date": "Invalid datetime format."})
        elif "due_date" in data:
            dt_to_process = data["due_date"]

        if dt_to_process is None:
            return data

        # --- Force naive if input is aware ---
        if timezone.is_aware(dt_to_process):
            dt_to_process = timezone.make_naive(dt_to_process, pytz.UTC)
            print(f"DEBUG: **FIX APPLIED**: Forced input to naive → {dt_to_process}")

        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        # --- Convert naive to aware using localize and normalize ---
        if timezone.is_naive(dt_to_process):
            aware_dt = user_tz.localize(dt_to_process, is_dst=None)
            aware_dt = user_tz.normalize(aware_dt)
            print(f"DEBUG: Naive input, localized to user → {aware_dt}")
        else:
            aware_dt = dt_to_process
            print(f"DEBUG: Already aware input → {aware_dt}")

        # --- Store in UTC ---
        data["due_date"] = aware_dt.astimezone(pytz.UTC)
        print(f"DEBUG: Final due_date (UTC) → {data['due_date']}")

        # --- Convert reminder_time if provided ---
        reminder_time = data.get("reminder_time")
        if reminder_time:
            if isinstance(reminder_time, str):
                try:
                    h, m, s = map(int, reminder_time.split(":"))
                    reminder_time = time(h, m, s)
                except Exception:
                    raise serializers.ValidationError({"reminder_time": "Invalid time format. Use HH:MM:SS."})

            local_due_date = data["due_date"].astimezone(user_tz).date()
            reminder_dt_local = user_tz.localize(datetime.combine(local_due_date, reminder_time), is_dst=None)
            reminder_dt_utc = reminder_dt_local.astimezone(pytz.UTC)
            data["reminder_time"] = reminder_dt_utc.time()
            print(f"DEBUG: Final reminder_time (UTC component) → {data['reminder_time']}")

        return data

    # ---------------------------
    # UPDATE LOGIC
    # ---------------------------
    def update(self, instance, validated_data):
        old_due_date = instance.due_date
        new_due_date = validated_data.get("due_date", old_due_date)
        user_tz = self.get_user_timezone(instance)

        # Proceed with normal update
        instance = super().update(instance, validated_data)

        # ✅ Reset overdue status if due date moved to the future
        now_utc = timezone.now()
        if instance.status == "overdue" and new_due_date > now_utc:
            instance.status = "pending"
            instance.overdue_reason = None
            instance.save(update_fields=["status", "overdue_reason"])
            print(f"DEBUG: Task {instance.id} status reset to 'pending' (new due_date is in the future)")

        # ✅ Set default reminder_time if not changed or now invalid
        if "reminder_time" not in validated_data:
            default_reminder_dt = new_due_date - timedelta(minutes=15)
            instance.reminder_time = default_reminder_dt.time()
            instance.reminder_sent = False
            instance.save(update_fields=["reminder_time", "reminder_sent"])
            print(f"DEBUG: Default reminder set to 15 minutes before due_date → {instance.reminder_time}")

        else:
            # Ensure reminder is still before due_date
            reminder_dt = datetime.combine(new_due_date.date(), instance.reminder_time)
            if reminder_dt >= new_due_date:
                default_reminder_dt = new_due_date - timedelta(minutes=15)
                instance.reminder_time = default_reminder_dt.time()
                instance.save(update_fields=["reminder_time"])
                print(f"DEBUG: Reminder adjusted to 15 minutes before due_date → {instance.reminder_time}")

        return instance

    # ---------------------------
    # TO REPRESENTATION
    # ---------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data



class AiTaskSerializer(serializers.ModelSerializer):
    ai_subtasks = AiSubTaskSerializer(many=True, read_only=True)
    # keep DRF DateTime fields for automatic validation on output
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    reminder_time = serializers.TimeField(required=False, allow_null=True)

    class Meta:
        model = AiTask
        fields = [
            'id',
            'ai_goal',
            'title',
            'description',
            'due_date',
            'status',
            'overdue_reason',
            'completed_at',
            'ai_subtasks',
            'task_timeline',
            'reminder_time',
            'last_updated',
            'reminder_sent',
        ]

    def get_user_timezone(self, obj=None):
        """
        Return a pytz timezone object for the user, falling back to UTC.
        Prefer AiGoal -> user -> timezone, otherwise use request.user.timezone.
        """
        user_tz = None
        # Prefer AiGoal -> user timezone when obj (instance) is available
        if obj and getattr(obj, "ai_goal", None) and getattr(obj.ai_goal, "user", None):
            user_tz = getattr(obj.ai_goal.user, "timezone", None)
            if user_tz:
                print(f"DEBUG: Found user timezone from AiGoal.user → {user_tz}")
        # Else try request.user
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            if user_tz:
                print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            print(f"DEBUG: Using pytz timezone object → {tz}")
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    # --- Return values to frontend in user local timezone as ISO strings ---
    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Convert due_date and completed_at to user's timezone and present as ISO strings
        user_tz = self.get_user_timezone(instance)
        if instance.due_date:
            local_due = localtime(instance.due_date, user_tz)
            # ISO includes offset, e.g. '2025-09-10T23:00:00+03:00'
            data['due_date'] = local_due.isoformat()
        if instance.completed_at:
            local_completed = localtime(instance.completed_at, user_tz)
            data['completed_at'] = local_completed.isoformat()

        if self.context.get("include_subtasks", False):
            data["ai_subtasks"] = AiSai_tasksubTaskSerializer(instance.ai_subtasks.all(), many=True).data

        return data

    # --- Work with raw input to detect whether frontend provided a timezone or not ---
    def validate(self, data):
        """
        Ensure incoming due_date is interpreted as user's local time when frontend sends a naive string.
        If frontend sent timezone info, respect it and normalize to UTC for storage.
        """
        # raw string from request (if available)
        raw_due = None
        request = self.context.get("request")
        if request:
            # don't raise if key is missing; .get returns None
            raw_due = request.data.get('due_date')

        # DRF may already have parsed `due_date` into a datetime object in data
        parsed_due = data.get('due_date')

        print(f"DEBUG: Raw request due_date string → {raw_due!r}")
        print(f"DEBUG: Parsed due_date before validation → {parsed_due!r} (type={type(parsed_due)})")

        if raw_due is None and parsed_due is None:
            # nothing to do
            return data

        # Determine user timezone
        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        # If raw_due is a string and lacks timezone info, parse it as user's local time
        if isinstance(raw_due, str):
            # crude check: see if raw string contains timezone indicator 'Z' or +HH:MM or -HH:MM
            has_tz_hint = (
                'Z' in raw_due
                or '+' in raw_due[-6:]  # e.g. +03:00 at end
                or '-' in raw_due[-6:]   # e.g. -05:00 at end
            )
            if not has_tz_hint:
                # treat raw string as user-local naive datetime
                naive = parse_datetime(raw_due)
                if naive is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if naive.tzinfo is None:
                    localized = make_aware(naive, timezone=user_tz)
                    print(f"DEBUG: Localized naive (from raw string) → {localized} (user tz)")
                else:
                    localized = naive
                # convert to UTC for storage
                final_due = localized.astimezone(pytz.UTC)
                print(f"DEBUG: Final due_date (converted to UTC) → {final_due}")
                data['due_date'] = final_due
            else:
                # raw string had tz info — let DRF's parsing (parsed_due) handle it if available
                if parsed_due is None:
                    # fallback: parse raw and normalize to UTC
                    dt = parse_datetime(raw_due)
                    if dt is None:
                        raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                    if dt.tzinfo is None:
                        dt = make_aware(dt, timezone=user_tz)
                    data['due_date'] = dt.astimezone(pytz.UTC)
                    print(f"DEBUG: Parsed raw with tz hint and converted to UTC → {data['due_date']}")
                else:
                    # parsed_due exists (likely aware) — normalize to UTC
                    data['due_date'] = parsed_due.astimezone(pytz.UTC)
                    print(f"DEBUG: Parsed (aware) converted to UTC → {data['due_date']}")
        else:
            # raw_due not provided or not a string, rely on parsed_due (could be datetime object)
            if parsed_due:
                # If parsed_due is naive, assume user local time
                if getattr(parsed_due, 'tzinfo', None) is None:
                    localized = make_aware(parsed_due, timezone=user_tz)
                    final_due = localized.astimezone(pytz.UTC)
                    data['due_date'] = final_due
                    print(f"DEBUG: Parsed naive -> localized -> converted to UTC → {final_due}")
                else:
                    # already aware; normalize to UTC
                    data['due_date'] = parsed_due.astimezone(pytz.UTC)
                    print(f"DEBUG: Parsed aware -> normalized to UTC → {data['due_date']}")

        # compute reminder_time (30 min before stored UTC due)
        if data.get('due_date'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()

        # prevent regression of completed status
        if self.instance:
            if self.instance.status == 'completed' and data.get('status') != 'completed':
                raise serializers.ValidationError("Cannot move a completed task back to another status.")

        return data

class CreateGoalSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=AiGoal.CATEGORY_CHOICES, required=False, allow_null=True, default=None)
    progress = serializers.IntegerField(default=0)

    class Meta:
        model = Goal
        fields = ['title', 'description', 'category','progress' ]

    def create(self, validated_data):
        user = self.context['request'].user
        goal = Goal.objects.create(user=user, **validated_data)
        return goal


class GoalSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    category = serializers.ChoiceField(choices=AiGoal.CATEGORY_CHOICES, required=False, allow_null=True, default=None)
   

    class Meta:
        model = Goal
        fields = [
            'id',
            'user',
            'title',
            'description',
            'category',
            'progress',
            'created_at',
            'updated_at',
            'tasks',
            'tag'
        ]

class CreateAiGoalSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=AiGoal.CATEGORY_CHOICES, required=False, allow_null=True, default=None)
    tag = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # ✅ Add this line

    class Meta:
        model = AiGoal
        fields = ['title', 'description', 'category', 'progress', 'tag']

    

    def create(self, validated_data):
        request_user = self.context["request"].user
        ai_goal = validated_data.get("title")

        # Fetch AI insights
        insights = get_insights(ai_goal)

       # Ensure AI-provided category is valid
        if not validated_data.get("category") and isinstance(insights, dict) and "goal_category" in insights:

            category = insights["goal_category"].lower()  # Convert to lowercase
            if category in dict(AiGoal.CATEGORY_CHOICES):
                validated_data["category"] = category
            else:
                raise serializers.ValidationError({"category": [f"'{insights['goal_category']}' is not a valid choice. Please select from {', '.join([choice[1] for choice in AiGoal.CATEGORY_CHOICES])}."] })

        validated_data["user"] = request_user
        return AiGoal.objects.create(**validated_data)


    
class AiGoalSerializer(serializers.ModelSerializer):
    ai_tasks = AiTaskSerializer(many=True, read_only=True)
    category = serializers.ChoiceField(choices=AiGoal.CATEGORY_CHOICES, required=False, allow_null=True, default=None)

    

    class Meta:
        model = AiGoal
        fields = [
            'id',
            'user',
            'title',
            'description',
            'category',
            'progress',
            'created_at',
            'updated_at',
            'ai_tasks',
            'tag'
        ]




class UserProfileSerializer(serializers.ModelSerializer):
    goals = GoalSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)
    ai_goals = AiGoalSerializer(many=True, read_only=True)
    ai_tasks = AiTaskSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'goals', 'tasks', 'ai_goals', 'ai_tasks']


class UpdateAiGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiGoal
        fields = ['title', 'description', 'category', 'progress']



class RoutineSerializer(serializers.ModelSerializer):
    tasks = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), many=True, required=False
    )
    subtasks = serializers.PrimaryKeyRelatedField(
        queryset=SubTask.objects.all(), many=True, required=False
    )
    ai_subtasks = serializers.PrimaryKeyRelatedField(
        queryset=AiSubTask.objects.all(), many=True, required=False
    )

    due_date = serializers.DateTimeField(write_only=True, required=False)
    name = serializers.CharField(required=False)
    start_date = serializers.DateField(required=False)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Routine
        fields = '__all__'

    # ---------------------------
    # HELPER METHOD
    # ---------------------------
    def get_user_timezone(self, obj=None):
        user_tz = None
        if obj and getattr(obj, "user", None) and getattr(obj.user, "timezone", None):
            user_tz = obj.user.timezone
        elif self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone

        if not user_tz:
            return pytz.UTC

        try:
            return pytz.timezone(user_tz)
        except Exception:
            return pytz.UTC

    # ---------------------------
    # VALIDATION
    # ---------------------------
    def validate(self, data):
        # Convert empty strings to None
        if data.get("custom_interval") == "":
            data["custom_interval"] = None
        if data.get("custom_unit") == "":
            data["custom_unit"] = None

        frequency = data.get("frequency")
        if frequency == "custom":
            if not data.get("custom_interval") or not data.get("custom_unit"):
                raise serializers.ValidationError(
                    "For custom frequency, both custom_interval and custom_unit are required."
                )
        else:
            data["custom_interval"] = None
            data["custom_unit"] = None

        user_tz = self.get_user_timezone(self.instance or None)
        base_date = timezone.localdate()  # today

        # Convert reminder_time to UTC
        reminder_time = data.get("reminder_time")
        if reminder_time:
            if isinstance(reminder_time, str):
                h, m, s = map(int, reminder_time.split(":"))
                reminder_time = time(h, m, s)

            local_dt = datetime.combine(base_date, reminder_time)
            local_dt = user_tz.localize(local_dt, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.UTC)
            data["reminder_time"] = utc_dt.time()

        # Convert time_of_day to UTC
        time_of_day = data.get("time_of_day")
        if time_of_day:
            if isinstance(time_of_day, str):
                h, m, s = map(int, time_of_day.split(":"))
                time_of_day = time(h, m, s)

            local_dt = datetime.combine(base_date, time_of_day)
            local_dt = user_tz.localize(local_dt, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.UTC)
            data["time_of_day"] = utc_dt.time()

        return data

    # ---------------------------
    # CREATE
    # ---------------------------
    def create(self, validated_data):
        tasks = validated_data.pop("tasks", [])
        subtasks = validated_data.pop("subtasks", [])
        ai_subtasks = validated_data.pop("ai_subtasks", [])

        # Check if ANY task/subtask was passed in the request body
        # This determines if we should auto-create a placeholder
        should_create_placeholder = not tasks and not subtasks and not ai_subtasks

        if not validated_data.get("name"):
            validated_data["name"] = f"{validated_data['frequency'].capitalize()} Routine"

        routine = Routine.objects.create(**validated_data)

        # --- Link existing tasks/subtasks if passed ---
        for task in tasks:
            task.routine = routine
            task.save()
        for subtask in subtasks:
            subtask.routine = routine
            subtask.save()
        for ai_subtask in ai_subtasks:
            ai_subtask.routine = routine
            ai_subtask.save()

        # --- Create *only a Task* placeholder if none were passed and a template exists ---
        if should_create_placeholder and getattr(routine, "subtask_template_title", None):
            Task.objects.create(
                user=routine.user,
                title=routine.subtask_template_title,
                description=getattr(routine, "subtask_template_description", "") or "",
                due_date=timezone.make_aware(datetime.combine(routine.start_date, routine.time_of_day or time(8, 0))),
                reminder_time=routine.reminder_time,
                routine=routine,
                status="pending",
            )
            
            # NOTE: You must REMOVE the blocks that create AiSubTask and SubTask
            # otherwise they will STILL run because routine.ai_subtasks.exists() is False

        routine.refresh_from_db()
        return routine

    # ---------------------------
    # UPDATE
    # ---------------------------
    def update(self, instance, validated_data):
        frequency = validated_data.get("frequency", instance.frequency)

        if frequency == "custom":
            custom_interval = validated_data.get("custom_interval", instance.custom_interval)
            custom_unit = validated_data.get("custom_unit", instance.custom_unit)
            start_date = validated_data.get("start_date", instance.start_date)

            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    start_date = instance.start_date

            if custom_unit == "days":
                end_date = start_date + timedelta(days=custom_interval)
            elif custom_unit == "weeks":
                end_date = start_date + timedelta(weeks=custom_interval)
            elif custom_unit == "months":
                end_date = start_date + relativedelta(months=custom_interval)
            else:
                end_date = validated_data.get("end_date", instance.end_date)

            validated_data["end_date"] = end_date

        return super().update(instance, validated_data)



class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = "__all__"
        read_only_fields = ["template"]

class DailyTemplateSerializer(serializers.ModelSerializer):
    activities = DailyActivitySerializer(many=True, read_only=True)

    class Meta:
        model = DailyTemplate
        fields = "__all__"
        read_only_fields = ["user"]


class DailyActivityHistorySerializer(serializers.ModelSerializer):
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    template = serializers.IntegerField(source='activity.template.id', read_only=True)


    class Meta:
        model = DailyActivityHistory
        fields = ['id', 'activity', 'activity_title', 'template' ,'date', 'completed', 'completed_at']