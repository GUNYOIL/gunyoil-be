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


class WorkoutSetUpdateSerializer(serializers.Serializer):
    set_id = serializers.IntegerField()
    weight = serializers.FloatField(required=False)
    reps = serializers.IntegerField(required=False)
    is_completed = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not {'weight', 'reps', 'is_completed'} & set(attrs.keys()):
            raise serializers.ValidationError('At least one field to update is required.')
        return attrs


class TodayWorkoutSaveSerializer(serializers.Serializer):
    is_completed = serializers.BooleanField(required=False)
    sets = WorkoutSetUpdateSerializer(many=True, required=False)

    def validate(self, attrs):
        if 'is_completed' not in attrs and 'sets' not in attrs:
            raise serializers.ValidationError('is_completed or sets is required.')
        return attrs
