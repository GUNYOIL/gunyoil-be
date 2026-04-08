from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer

from config.api import success_response, error_response
from .models import Exercise
from .serializers import ExerciseSerializer


class ExerciseListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExerciseSerializer

    def get(self, request):
        queryset = Exercise.objects.filter(is_active=True)

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category.upper())

        target_muscle = request.query_params.get('target_muscle')
        if target_muscle:
            queryset = queryset.filter(target_muscle__icontains=target_muscle)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        serializer = ExerciseSerializer(queryset, many=True)
        return success_response(serializer.data)

class AdminExerciseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="운동 기구 추가 (어드민)",
        request=inline_serializer(
            name='CreateExerciseRequest',
            fields={
                'code': serializers.CharField(),
                'name': serializers.CharField(),
                'category': serializers.CharField(),
                'target_muscle': serializers.CharField(),
            }
        )
    )
    def post(self, request):
        code = request.data.get('code')
        name = request.data.get('name')
        category = request.data.get('category', '').upper()
        target_muscle = request.data.get('target_muscle')

        if not (code and name and category and target_muscle):
            return error_response('모든 필드(code, name, category, target_muscle)를 입력해주세요.')

        # 카테고리가 Category Choices에 있는지 검증은 프론트 단 또는 모델 저장시 수행
        exercise = Exercise.objects.create(
            code=code,
            name=name,
            category=category,
            target_muscle=target_muscle,
            is_active=True
        )
        return success_response({'id': exercise.id}, '운동 종류가 정상적으로 추가되었습니다.')
