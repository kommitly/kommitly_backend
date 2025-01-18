from rest_framework import serializers
from .models import Goal, Task

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



class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['goal', 'title', 'due_date', 'status']  # Include fields necessary for task creation

    def create(self, validated_data):
        # This will associate the task with an existing goal
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

