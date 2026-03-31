from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Exercise
from .serializers import ExerciseSerializer

class ExerciseListView(APIView):
    permission_classes = [IsAuthenticated] # 로그인한 학생만 기구 목록 확인 가능

    def get(self, request):
        queryset = Exercise.objects.all()
        
        # 만약 프론트에서 ?category=CHEST 라고 요청하면 가슴 운동만 필터링!
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category.upper())
            
        serializer = ExerciseSerializer(queryset, many=True)
        return Response(serializer.data)
