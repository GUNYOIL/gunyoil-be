from rest_framework import serializers
from .models import Routine, RoutineDetail

class RoutineDetailSerializer(serializers.ModelSerializer):
    # 기구의 ID뿐만 아니라, 실제 기구 이름(예: 랫풀다운)도 보기 좋게 함께 반환합니다.
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = RoutineDetail
        fields = ['id', 'exercise', 'exercise_name', 'target_weight', 'target_reps', 'target_sets', 'order']

class RoutineSerializer(serializers.ModelSerializer):
    # Routine 안에 속한 RoutineDetail 들을 List 배열 안에 싹 다 묶어서 같이 보여줌
    details = RoutineDetailSerializer(many=True, read_only=True)
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Routine
        fields = ['id', 'day_of_week', 'day_name', 'details']
