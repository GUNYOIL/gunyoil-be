from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from diet.models import ProteinLog
from routines.models import Routine
from workouts.models import DailyLog, WorkoutSet
from workouts.serializers import DailyLogSerializer, TodayLogSerializer

from .serializers import (
    CustomTokenObtainPairSerializer,
    DashboardSerializer,
    GrassEntrySerializer,
    PasswordChangeSerializer,
    UserSerializer,
)


DEFAULT_PROTEIN_MULTIPLIER = Decimal('1.6')


def _quantize(value):
    return value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def _get_target_amount(user):
    if not user.weight:
        return None
    return _quantize(Decimal(str(user.weight)) * DEFAULT_PROTEIN_MULTIPLIER)


def _build_today_workout(user, today):
    log = DailyLog.objects.filter(user=user, date=today).prefetch_related('sets__exercise').first()
    if log:
        return TodayLogSerializer(log).data

    weekday = today.weekday()
    routine = Routine.objects.filter(user=user, day_of_week=weekday).prefetch_related('details__exercise').first()
    if not routine:
        return {
            'id': None,
            'date': today,
            'is_completed': False,
            'sets': [],
        }

    sets = []
    set_id = -1
    for detail in routine.details.all():
        for set_number in range(1, detail.target_sets + 1):
            sets.append(
                {
                    'id': set_id,
                    'exercise': detail.exercise_id,
                    'exercise_name': detail.exercise.name,
                    'set_number': set_number,
                    'weight': detail.target_weight,
                    'reps': detail.target_reps,
                    'is_completed': False,
                }
            )
            set_id -= 1

    return {
        'id': None,
        'date': today,
        'is_completed': False,
        'sets': sets,
    }


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "회원가입 성공"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OnboardingDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(onboarding_completed=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OnboardingCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.onboarding_completed = True
        user.save()
        return Response(
            {"message": "온보딩이 완료되었습니다.", "onboarding_completed": True},
            status=status.HTTP_200_OK,
        )


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        today_workout = _build_today_workout(request.user, today)
        recent_workouts = DailyLog.objects.filter(user=request.user, is_completed=True).order_by('-date')[:5]
        protein_logs = ProteinLog.objects.filter(user=request.user, date=today)
        consumed_amount = _quantize(sum((log.amount for log in protein_logs), Decimal('0.0')))
        target_amount = _get_target_amount(request.user)

        progress_percent = 0
        is_target_completed = False
        if target_amount is not None and target_amount > 0:
            progress_percent = min(int((consumed_amount / target_amount) * 100), 100)
            is_target_completed = consumed_amount >= target_amount

        serializer = DashboardSerializer(
            {
                'date': today,
                'today_workout': today_workout,
                'protein': {
                    'target_amount': target_amount,
                    'consumed_amount': consumed_amount,
                    'progress_percent': progress_percent,
                    'is_target_completed': is_target_completed,
                },
                'recent_workouts': DailyLogSerializer(recent_workouts, many=True).data,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class GrassView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = DailyLog.objects.filter(user=request.user).order_by('date')
        serializer = GrassEntrySerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
