from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DailyLog
from .serializers import DailyLogSerializer

class WorkoutHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    # 내 전체 운동 기록 이력 (잔디 UI 달력 그리기용)
    def get(self, request):
        # 내가 '완료(is_completed=True)' 도장을 찍은 날짜들만 싹 다 가져오기
        logs = DailyLog.objects.filter(user=request.user, is_completed=True).order_by('date')
        serializer = DailyLogSerializer(logs, many=True)
        return Response(serializer.data)
