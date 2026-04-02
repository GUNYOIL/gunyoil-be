from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api import error_response, success_response
from .models import Routine, RoutineDetail
from .serializers import RoutineSerializer


class UserRoutineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        routines = Routine.objects.filter(user=request.user).order_by('day_of_week')
        serializer = RoutineSerializer(routines, many=True)
        return success_response(serializer.data)

    def put(self, request):
        data = request.data
        if not isinstance(data, list):
            return error_response('리스트([]) 형태로 데이터를 보내주세요.', status_code=status.HTTP_400_BAD_REQUEST)

        Routine.objects.filter(user=request.user).delete()

        for routine_data in data:
            day = routine_data.get('day_of_week')
            routine = Routine.objects.create(user=request.user, day_of_week=day)

            details_data = routine_data.get('details', [])
            for detail in details_data:
                RoutineDetail.objects.create(
                    routine=routine,
                    exercise_id=detail['exercise'],
                    target_weight=detail.get('target_weight', 0),
                    target_reps=detail.get('target_reps', 0),
                    target_sets=detail.get('target_sets', 0),
                    order=detail.get('order', 0),
                )

        new_routines = Routine.objects.filter(user=request.user).order_by('day_of_week')
        serializer = RoutineSerializer(new_routines, many=True)
        return success_response(serializer.data, '루틴이 저장되었습니다.', status.HTTP_201_CREATED)
