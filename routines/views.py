from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Routine, RoutineDetail
from .serializers import RoutineSerializer

class UserRoutineView(APIView):
    permission_classes = [IsAuthenticated]

    # 1. 내 모든 요일의 루틴 조회 (GET /me/routines/)
    def get(self, request):
        routines = Routine.objects.filter(user=request.user).order_by('day_of_week')
        serializer = RoutineSerializer(routines, many=True)
        return Response(serializer.data)

    # 2. 내 루틴 전체 설정/수정 (PUT /me/routines/)
    def put(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "리스트([]) 형태로 데이터를 보내주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 1) 먼저 로그인한 회원의 기존 루틴을 전부 깔끔히 삭제 (초기화)
        Routine.objects.filter(user=request.user).delete()

        # 2) 새로 들어온 JSON 데이터를 뜯어서 요일별 루틴 생성
        for routine_data in data:
            day = routine_data.get('day_of_week')
            routine = Routine.objects.create(user=request.user, day_of_week=day)
            
            # 3) 방금 만든 요일에 맞춰서 속해있는 기구 운동 정보 쏙쏙 넣기
            details_data = routine_data.get('details', [])
            for detail in details_data:
                RoutineDetail.objects.create(
                    routine=routine,
                    exercise_id=detail['exercise'], # 프론트가 보내준 기구의 ID
                    target_weight=detail.get('target_weight', 0),
                    target_reps=detail.get('target_reps', 0),
                    target_sets=detail.get('target_sets', 0),
                    order=detail.get('order', 0)
                )

        # 4) 방금 저장된 최신 루틴을 다시 가져와서 응답으로 뱉어줌
        new_routines = Routine.objects.filter(user=request.user).order_by('day_of_week')
        serializer = RoutineSerializer(new_routines, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
