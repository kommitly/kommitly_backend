from rest_framework import serializers
from .models import Goal, Task, AiGoal, AiTask, SubTask, AiSubTask, Routine
from users.models import User
from django.utils.timezone import make_aware, datetime
import pytz
import logging
from ai_insights.utils import get_insights
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta
from .timezone import get_timezone
from rest_framework import serializers
from .models import Task  # Adjust the import based on your project structure
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubTask
        fields = [
            'id',
            'task',
            'title',
            'description',
            'due_date',
            'status',
            'overdue_reason',
            'completed_at',
            'reminder_time',
            'reminder_sent',
            'last_updated',
            'ai_answer',
            'routine'
        ]

    def get_user_timezone(self, obj=None):
        """
        Return pytz timezone for the subtask's parent task.user,
        or fallback to request.user or UTC.
        """
        user_tz = None

        # Case 1: Backtrack through Task → User
        if obj and getattr(obj, "task", None) and getattr(obj.task, "user", None):
            if getattr(obj.task.user, "timezone", None):
                user_tz = obj.task.user.timezone
                print(f"DEBUG: Found user timezone from SubTask.task.user → {user_tz}")

        # Case 2: From request.user
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    def validate(self, data):
        raw_due = None
        request = self.context.get("request")
        if request:
            raw_due = request.data.get('due_date')

        parsed_due = data.get('due_date')
        print(f"DEBUG: Raw request due_date string → {raw_due!r}")
        print(f"DEBUG: Parsed due_date before validation → {parsed_due!r}")

        if raw_due is None and parsed_due is None:
            return data

        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        if isinstance(raw_due, str):
            has_tz_hint = (
                'Z' in raw_due
                or '+' in raw_due[-6:]
                or '-' in raw_due[-6:]
            )
            if not has_tz_hint:
                naive = parse_datetime(raw_due)
                if naive is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if naive.tzinfo is None:
                    localized = make_aware(naive, timezone=user_tz)
                else:
                    localized = naive
                final_due = localized.astimezone(pytz.UTC)
                data['due_date'] = final_due
            else:
                dt = parsed_due or parse_datetime(raw_due)
                if dt is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if dt.tzinfo is None:
                    dt = make_aware(dt, timezone=user_tz)
                data['due_date'] = dt.astimezone(pytz.UTC)
        else:
            if parsed_due:
                if getattr(parsed_due, 'tzinfo', None) is None:
                    localized = make_aware(parsed_due, timezone=user_tz)
                    final_due = localized.astimezone(pytz.UTC)
                    data['due_date'] = final_due
                else:
                    data['due_date'] = parsed_due.astimezone(pytz.UTC)

        # auto compute reminder_time if not provided
        if data.get('due_date') and not data.get('reminder_time'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()

        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_tz = self.get_user_timezone(instance)

        if instance.due_date:
            local_due = localtime(instance.due_date, user_tz)
            data['due_date'] = local_due.isoformat()
        if instance.completed_at:
            local_completed = localtime(instance.completed_at, user_tz)
            data['completed_at'] = local_completed.isoformat()

        return data



class AiSubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiSubTask
        fields = "__all__"
        read_only_fields = ["ai_task"]

    def create(self, validated_data):
        ai_task_id = self.context.get("ai_task_id")
        if ai_task_id:
            validated_data["ai_task_id"] = ai_task_id
        return super().create(validated_data)

    def get_user_timezone(self, obj=None):
        """
        Return pytz timezone for the user via AiTask -> AiGoal -> User.
        Falls back to request.user or UTC.
        """
        user_tz = None

        # Case 1: From AiTask -> AiGoal -> User
        if obj and getattr(obj, "ai_task", None) and getattr(obj.ai_task, "ai_goal", None):
            user = getattr(obj.ai_task.ai_goal, "user", None)
            if user and getattr(user, "timezone", None):
                user_tz = user.timezone
                print(f"DEBUG: Found user timezone from AiTask.ai_goal.user → {user_tz}")

        # Case 2: From request.user
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

    def validate(self, data):
        raw_due = None
        request = self.context.get("request")
        if request:
            raw_due = request.data.get('due_date')

        parsed_due = data.get('due_date')
        print(f"DEBUG: Raw request due_date string → {raw_due!r}")
        print(f"DEBUG: Parsed due_date before validation → {parsed_due!r}")

        if raw_due is None and parsed_due is None:
            return data

        # backtrack user timezone
        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        if isinstance(raw_due, str):
            has_tz_hint = (
                'Z' in raw_due
                or '+' in raw_due[-6:]
                or '-' in raw_due[-6:]
            )
            if not has_tz_hint:
                naive = parse_datetime(raw_due)
                if naive is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if naive.tzinfo is None:
                    localized = make_aware(naive, timezone=user_tz)
                    print(f"DEBUG: Localized naive (subtask) → {localized}")
                else:
                    localized = naive
                final_due = localized.astimezone(pytz.UTC)
                data['due_date'] = final_due
                print(f"DEBUG: Final subtask due_date (UTC) → {final_due}")
            else:
                dt = parsed_due or parse_datetime(raw_due)
                if dt is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if dt.tzinfo is None:
                    dt = make_aware(dt, timezone=user_tz)
                data['due_date'] = dt.astimezone(pytz.UTC)
                print(f"DEBUG: Parsed subtask aware → {data['due_date']}")
        else:
            if parsed_due:
                if getattr(parsed_due, 'tzinfo', None) is None:
                    localized = make_aware(parsed_due, timezone=user_tz)
                    final_due = localized.astimezone(pytz.UTC)
                    data['due_date'] = final_due
                    print(f"DEBUG: Parsed subtask naive → UTC {final_due}")
                else:
                    data['due_date'] = parsed_due.astimezone(pytz.UTC)
                    print(f"DEBUG: Parsed subtask aware → UTC {data['due_date']}")

        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_tz = self.get_user_timezone(instance)

        if instance.due_date:
            local_due = localtime(instance.due_date, user_tz)
            data['due_date'] = local_due.isoformat()
        if instance.completed_at:
            local_completed = localtime(instance.completed_at, user_tz)
            data['completed_at'] = local_completed.isoformat()

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
            'tag'
         
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
            'id',
            'goal',
            'user',
            'title',
            'description',
            'due_date',
            'status',
            'completed_at',
            'subtasks',
            'overdue_reason',
            'task_timeline',
            'reminder_time',
            'last_updated',
            'reminder_sent',
            'tag',
            'ai_answer',
            'routine'
        ]

    def get_user_timezone(self, obj=None):
        """
        Return pytz timezone for the task's user, or fallback to request.user or UTC.
        """
        user_tz = None

        # Case 1: From Task.user
        if obj and getattr(obj, "user", None) and getattr(obj.user, "timezone", None):
            user_tz = obj.user.timezone
            print(f"DEBUG: Found user timezone from Task.user → {user_tz}")

        # Case 2: From request.user
        if not user_tz and self.context.get("request") and hasattr(self.context["request"].user, "timezone"):
            user_tz = self.context["request"].user.timezone
            print(f"DEBUG: Found user timezone from request.user → {user_tz}")

        if not user_tz:
            print("DEBUG: No user timezone found, defaulting to UTC")
            return pytz.UTC

        try:
            tz = pytz.timezone(user_tz)
            return tz
        except Exception as e:
            print(f"DEBUG: Invalid timezone '{user_tz}', falling back to UTC. Error: {e}")
            return pytz.UTC

    def validate(self, data):
        raw_due = None
        request = self.context.get("request")
        if request:
            raw_due = request.data.get('due_date')

        parsed_due = data.get('due_date')
        print(f"DEBUG: Raw request due_date string → {raw_due!r}")
        print(f"DEBUG: Parsed due_date before validation → {parsed_due!r}")

        if raw_due is None and parsed_due is None:
            return data

        user_tz = self.get_user_timezone(self.instance or None)
        print(f"DEBUG: Effective user timezone → {user_tz}")

        if isinstance(raw_due, str):
            has_tz_hint = (
                'Z' in raw_due
                or '+' in raw_due[-6:]
                or '-' in raw_due[-6:]
            )
            if not has_tz_hint:
                naive = parse_datetime(raw_due)
                if naive is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if naive.tzinfo is None:
                    localized = make_aware(naive, timezone=user_tz)
                else:
                    localized = naive
                final_due = localized.astimezone(pytz.UTC)
                data['due_date'] = final_due
            else:
                dt = parsed_due or parse_datetime(raw_due)
                if dt is None:
                    raise serializers.ValidationError({"due_date": "Invalid datetime format."})
                if dt.tzinfo is None:
                    dt = make_aware(dt, timezone=user_tz)
                data['due_date'] = dt.astimezone(pytz.UTC)
        else:
            if parsed_due:
                if getattr(parsed_due, 'tzinfo', None) is None:
                    localized = make_aware(parsed_due, timezone=user_tz)
                    final_due = localized.astimezone(pytz.UTC)
                    data['due_date'] = final_due
                else:
                    data['due_date'] = parsed_due.astimezone(pytz.UTC)

        # auto compute reminder_time (30 min before due_date)
        if data.get('due_date') and not data.get('reminder_time'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()

        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_tz = self.get_user_timezone(instance)

        if instance.due_date:
            local_due = localtime(instance.due_date, user_tz)
            data['due_date'] = local_due.isoformat()
        if instance.completed_at:
            local_completed = localtime(instance.completed_at, user_tz)
            data['completed_at'] = local_completed.isoformat()

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
    tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    subtasks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
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

    def validate(self, data):
        frequency = data.get("frequency")

        if frequency == "custom":
            if not data.get("custom_interval") or not data.get("custom_unit"):
                raise serializers.ValidationError(
                    "For custom frequency, both custom_interval and custom_unit are required."
                )
        return data

    def create(self, validated_data):
        tasks = validated_data.pop("tasks", [])
        subtasks = validated_data.pop("subtasks", [])
        ai_subtasks = validated_data.pop("ai_subtasks", [])
        due_date = validated_data.pop("due_date", None)

        if due_date:
            validated_data["start_date"] = due_date.date()
            validated_data["time_of_day"] = due_date.time()
            if validated_data.get("frequency") == "weekly":
                validated_data["day_of_week"] = due_date.weekday()

            if not validated_data.get("end_date"):
                if validated_data["frequency"] == "daily":
                    validated_data["end_date"] = due_date.date() + timedelta(days=7)
                elif validated_data["frequency"] == "weekly":
                    validated_data["end_date"] = due_date.date() + timedelta(weeks=4)
                elif validated_data["frequency"] == "monthly":
                    validated_data["end_date"] = due_date.date() + timedelta(days=90)
                elif validated_data["frequency"] == "custom":
                    interval = validated_data.get("custom_interval", 1)
                    unit = validated_data.get("custom_unit")
                    if unit == "days":
                        validated_data["end_date"] = due_date.date() + timedelta(days=interval * 7)
                    elif unit == "weeks":
                        validated_data["end_date"] = due_date.date() + timedelta(weeks=interval * 4)
                    elif unit == "months":
                        validated_data["end_date"] = due_date.date() + timedelta(days=interval * 90)

        if not validated_data.get("name"):
            validated_data["name"] = f"{validated_data['frequency'].capitalize()} Routine"

        routine = Routine.objects.create(**validated_data)

        for task in tasks:
            task.routine = routine
            task.save()

        for subtask in subtasks:
            subtask.routine = routine
            subtask.save()

        for ai_subtask in ai_subtasks:
            ai_subtask.routine = routine
            ai_subtask.save()

        return routine
