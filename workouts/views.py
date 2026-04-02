import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api import error_response, success_response
from routines.models import Routine

from .models import DailyLog, WorkoutSet
from .serializers import (
    DailyLogSerializer,
    TodayLogSerializer,
    TodayWorkoutSaveSerializer,
    WorkoutSetSerializer,
    WorkoutSetUpdateSerializer,
)


class WorkoutHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = DailyLog.objects.filter(user=request.user, is_completed=True).order_by('date')
        serializer = DailyLogSerializer(logs, many=True)
        return success_response(serializer.data)


class TodayWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.date.today()
        weekday = today.weekday()

        log, created = DailyLog.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={'is_completed': False},
        )

        if created:
            today_routine = Routine.objects.filter(user=request.user, day_of_week=weekday).first()
            if today_routine:
                for detail in today_routine.details.all():
                    for i in range(1, detail.target_sets + 1):
                        WorkoutSet.objects.create(
                            daily_log=log,
                            exercise=detail.exercise,
                            set_number=i,
                            weight=detail.target_weight,
                            reps=detail.target_reps,
                            is_completed=False,
                        )

        return success_response(TodayLogSerializer(log).data)

    def put(self, request):
        today = datetime.date.today()
        log = DailyLog.objects.filter(user=request.user, date=today).first()

        if not log:
            return error_response('오늘의 운동 기록이 없습니다.', code='workout_log_not_found', status_code=status.HTTP_404_NOT_FOUND)

        serializer = TodayWorkoutSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for set_data in serializer.validated_data.get('sets', []):
            try:
                workout_set = WorkoutSet.objects.get(id=set_data['set_id'], daily_log=log)
            except WorkoutSet.DoesNotExist:
                return error_response(
                    f"Workout set {set_data['set_id']} not found.",
                    code='workout_set_not_found',
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if 'weight' in set_data:
                workout_set.weight = set_data['weight']
            if 'reps' in set_data:
                workout_set.reps = set_data['reps']
            if 'is_completed' in set_data:
                workout_set.is_completed = set_data['is_completed']
            workout_set.save()

        if 'is_completed' in serializer.validated_data:
            log.is_completed = serializer.validated_data['is_completed']
        log.save()

        return success_response(TodayLogSerializer(log).data, '오늘 운동 기록이 저장되었습니다.')


class TodayWorkoutSetCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WorkoutSetUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            workout_set = WorkoutSet.objects.get(
                id=serializer.validated_data['set_id'],
                daily_log__user=request.user,
                daily_log__date=datetime.date.today(),
            )
        except WorkoutSet.DoesNotExist:
            return error_response('Workout set not found for today.', code='workout_set_not_found', status_code=status.HTTP_404_NOT_FOUND)

        if 'weight' in serializer.validated_data:
            workout_set.weight = serializer.validated_data['weight']
        if 'reps' in serializer.validated_data:
            workout_set.reps = serializer.validated_data['reps']
        if 'is_completed' in serializer.validated_data:
            workout_set.is_completed = serializer.validated_data['is_completed']

        workout_set.save()
        return success_response(WorkoutSetSerializer(workout_set).data, '세트 기록이 저장되었습니다.')
