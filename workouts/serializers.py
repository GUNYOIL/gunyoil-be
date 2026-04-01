from rest_framework import serializers
from .models import DailyLog, WorkoutSet

class WorkoutSetSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = WorkoutSet
        fields = ['id', 'exercise', 'exercise_name', 'set_number', 'weight', 'reps', 'is_completed']

class TodayLogSerializer(serializers.ModelSerializer):
    sets = WorkoutSetSerializer(many=True, read_only=True)

    class Meta:
        model = DailyLog
        fields = ['id', 'date', 'is_completed', 'sets']

class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = ['date', 'is_completed']