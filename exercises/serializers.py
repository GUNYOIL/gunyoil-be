from rest_framework import serializers
from .models import Exercise

class ExerciseSerializer(serializers.ModelSerializer):
    # 'CHEST' 대신 '가슴' 이라는 예쁜 한글 이름도 같이 보내주기 위한 설정
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'category', 'category_display', 'target_muscle']
