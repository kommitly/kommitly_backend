from rest_framework import serializers
from .models import Goal, Task, AiGoal, AiTask
from users.models import User
from django.utils.timezone import make_aware, datetime
import pytz


class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['goal','title', 'due_date', 'status', 'reminder_time']  # Include fields necessary for task creation

    def to_internal_value(self, data):
        if data.get('goal') == 0:
            data['goal'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = data['due_date'] - timedelta(minutes=30).time()  # Default: 30 min before due date
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
            data['reminder_time'] = data['due_date'] - timedelta(minutes=30).time()  # Default: 30 min before due date
        return data

class AiTaskSerializer(serializers.ModelSerializer):

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
            'task_timeline'
            ]

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = data['due_date'] - timedelta(minutes=30).time()  # Default: 30 min before due date
        return data



class CreateGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['title', 'description']  # Include only fields that are necessary for goal creation

    def create(self, validated_data):
        # You can assign the user here if you're using Django's authentication system
        user = self.context['request'].user  # Get the logged-in user from the request context
        goal = Goal.objects.create(user=user, **validated_data)
        return goal

class GoalSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 
            'user', 
            'title', 
            'description', 
            'created_at', 
            'updated_at',
            'tasks'

            ]



class CreateAiGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiGoal
        fields = ['title', 'description']  # Include only fields that are necessary for goal creation

    def create(self, validated_data):
        # You can assign the user here if you're using Django's authentication system
        validated_data["user"] = self.context["request"].user  # Ensure user is explicitly set
        return AiGoal.objects.create(**validated_data) 


class AiGoalSerializer(serializers.ModelSerializer):
    ai_tasks = AiTaskSerializer(many=True, read_only=True)  

    class Meta:
        model = AiGoal
        fields = [
            'id', 
            'user', 
            'title', 
            'description', 
            'created_at', 
            'updated_at',
            'ai_tasks'

            ]

class CreateAiTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiTask
        fields = ['ai_goal', 'title', 'due_date', 'status']  # Include fields necessary for task creation
    
    def to_internal_value(self, data):
        if data.get('ai_goal') == 0:
            data['ai_goal'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        if not data.get('reminder_time') and data.get('due_date'):
            data['reminder_time'] = (data['due_date'] - timedelta(minutes=30)).time()  # Default: 30 min before due date
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
        fields = ['title', 'description']
