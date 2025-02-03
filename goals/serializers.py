from rest_framework import serializers
from .models import Goal, Task, AiGoal, AiTask
from users.models import User


class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['goal', 'title', 'due_date', 'status']  # Include fields necessary for task creation

    def to_internal_value(self, data):
        if data.get('goal') == 0:
            data['goal'] = None
        return super().to_internal_value(data)

    def create(self, validated_data):
        task = Task.objects.create(**validated_data)
        return task

class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = [
            'id', 
            'goal', 
            'title', 
            'due_date', 
            'status', 
            'completed_at',
            'actionable_steps', 
            'task_timeline'
            ]

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

    def create(self, validated_data):
        # This will associate the task with an existing goal
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
