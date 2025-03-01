from rest_framework import serializers
from .models import Goal, Task, AiGoal, AiTask
from users.models import User
from django.utils.timezone import make_aware, datetime
from datetime import timedelta
import pytz
from ai_insights.utils import get_insights
from django.utils.timezone import localtime
from django.utils.timezone import now


class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['goal', 'title', 'due_date', 'status', 'reminder_time']

    def to_internal_value(self, data):
        if data.get('goal') == 0:
            data['goal'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()  # Fix timedelta usage
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        user_timezone = pytz.timezone(user.timezone) if user else pytz.UTC

        # Convert due_date and reminder_time to UTC
        due_date = validated_data['due_date']
        reminder_time = validated_data['reminder_time']
        reminder_datetime = datetime.combine(due_date.date(), reminder_time)
        reminder_datetime = make_aware(reminder_datetime, user_timezone)
        validated_data['due_date'] = reminder_datetime.astimezone(pytz.UTC)
        validated_data['reminder_time'] = reminder_datetime.astimezone(pytz.UTC).time()

        task = Task.objects.create(user=user, **validated_data)
        return task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'id',
            'goal',
            'user',
            'title',
            'due_date',
            'status',
            'completed_at',
            'actionable_steps',
            'task_timeline',
            'reminder_time'
        ]

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()
        return data

class AiTaskSerializer(serializers.ModelSerializer):
    completed_at = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    reminder_time = serializers.SerializerMethodField()

    class Meta:
        model = AiTask
        fields = [
            'id',
            'ai_goal',
            'title',
            'due_date',
            'status',
            'completed_at',
            'actionable_steps',
            'task_timeline',
            'reminder_time',
           
        ]

    def get_user_timezone(self, obj):
        """Fetch user's timezone from AiGoal if available, otherwise default to UTC."""
        if obj.ai_goal and obj.ai_goal.user and obj.ai_goal.user.timezone:
            return pytz.timezone(obj.ai_goal.user.timezone)
        return pytz.UTC

    def get_completed_at(self, obj):
        if obj.completed_at:
            return localtime(obj.completed_at, self.get_user_timezone(obj)).strftime('%Y-%m-%d %H:%M:%S')
        return None

    def get_due_date(self, obj):
        if obj.due_date:
            return localtime(obj.due_date, self.get_user_timezone(obj)).strftime('%Y-%m-%d %H:%M:%S')
        return None
    def get_reminder_time(self, obj):
        return obj.reminder_time.strftime('%H:%M:%S') if obj.reminder_time else None  # TimeField does not support timezone conversion

    def update(self, instance, validated_data):
        """
        When task status is updated, trigger progress recalculation.
      
        instance.status = validated_data.get('status', instance.status)
        instance.save()  # This automatically updates AiGoal progress
        return instance
          """
        
        """
        Handle status transitions and update goal progress.
        """
        previous_status = instance.status
        new_status = validated_data.get('status', instance.status)

        # If task was pending and gets modified, mark it as "in-progress"
        if previous_status == 'pending' and new_status not in ['completed', 'overdue']:
            instance.status = 'in-progress'

        # If marked as completed, set completion timestamp
        if new_status == 'completed' and instance.completed_at is None:
            instance.completed_at = now()

        instance = super().update(instance, validated_data)
        instance.save(update_fields=['status', 'completed_at'])  # Ensure status is saved

        if instance.ai_goal:
            instance.ai_goal.update_progress()  # Ensure progress is updated
        return instance

    def validate(self, data):
        """Ensure valid status transitions and default reminder time."""
        if "reminder_time" not in data and "due_date" in data:
            data["reminder_time"] = (data["due_date"] - timedelta(minutes=30)).time()

        # Prevent moving backwards in status
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
    progress = serializers.IntegerField(default=0)

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
            'tasks'
        ]

class CreateAiGoalSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=AiGoal.CATEGORY_CHOICES, required=False, allow_null=True, default=None)
    progress = serializers.IntegerField(default=0)

    class Meta:
        model = AiGoal
        fields = ['title', 'description', 'category', 'progress']

    

    def create(self, validated_data):
        request_user = self.context["request"].user
        ai_goal = validated_data.get("title")

        # Fetch AI insights
        insights = get_insights(ai_goal)

       # Ensure AI-provided category is valid
        if isinstance(insights, dict) and "goal_category" in insights:
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
    progress = serializers.IntegerField(default=0)
    

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
            'ai_tasks'
        ]


class CreateAiTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiTask
        fields = ['ai_goal', 'title', 'due_date', 'status']

    def to_internal_value(self, data):
        if data.get('ai_goal') == 0:
            data['ai_goal'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()
        return data

    def create(self, validated_data):
        ai_task = AiTask.objects.create(**validated_data)
        return ai_task


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
