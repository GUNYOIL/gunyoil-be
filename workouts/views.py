import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import DailyLog, WorkoutSet
from .serializers import DailyLogSerializer, TodayLogSerializer, WorkoutSetSerializer
from routines.models import Routine

class WorkoutHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = DailyLog.objects.filter(user=request.user, is_completed=True).order_by('date')
        serializer = DailyLogSerializer(logs, many=True)
        return Response(serializer.data)

class TodayWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.date.today()
        weekday = today.weekday()

        log, created = DailyLog.objects.get_or_create(
            user=request.user, 
            date=today,
            defaults={'is_completed': False}
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
                            is_completed=False
                        )

        return Response(TodayLogSerializer(log).data)

    def put(self, request):
        today = datetime.date.today()
        log = DailyLog.objects.filter(user=request.user, date=today).first()
        
        if not log:
            return Response({"error": "오늘의 운동 기록이 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        is_completed = request.data.get('is_completed', True)
        log.is_completed = is_completed
        log.save()
        
        return Response(TodayLogSerializer(log).data)

class WorkoutSetUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, set_id):
        try:
            workout_set = WorkoutSet.objects.get(id=set_id, daily_log__user=request.user)
        except WorkoutSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'weight' in request.data:
            workout_set.weight = request.data['weight']
        if 'reps' in request.data:
            workout_set.reps = request.data['reps']
        if 'is_completed' in request.data:  
            workout_set.is_completed = request.data['is_completed']
            
        workout_set.save()
        return Response(WorkoutSetSerializer(workout_set).data)
