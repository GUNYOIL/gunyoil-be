from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from config.api import error_response, success_response
from diet.models import ProteinLog
from routines.models import Routine
from workouts.models import DailyLog
from workouts.serializers import DailyLogSerializer, TodayLogSerializer

from .serializers import (
    CustomTokenObtainPairSerializer,
    DashboardSerializer,
    GrassEntrySerializer,
    OnboardingCompleteSerializer,
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


def _get_completion_percent(log):
    total_sets = log.sets.count()
    if total_sets == 0:
        return 100 if log.is_completed else 0

    completed_sets = log.sets.filter(is_completed=True).count()
    return int((completed_sets / total_sets) * 100)


class SignupView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(None, '회원가입 성공', status.HTTP_201_CREATED)
        return error_response('Request validation failed.', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, '프로필이 저장되었습니다.')
        return error_response('Request validation failed.', errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        request.user.delete()
        return success_response(None, '회원 탈퇴가 완료되었습니다.')


class OnboardingDraftView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(onboarding_completed=False)
        return success_response(serializer.data, '온보딩 초안이 저장되었습니다.')


class OnboardingCompleteView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OnboardingCompleteSerializer

    def post(self, request):
        user = request.user
        user.onboarding_completed = True
        user.save()
        return success_response({'onboarding_completed': True}, '온보딩이 완료되었습니다.')


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSerializer

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
        return success_response(serializer.data)


class GrassView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GrassEntrySerializer

    def get(self, request):
        logs = DailyLog.objects.filter(user=request.user).prefetch_related('sets').order_by('date')
        serializer = GrassEntrySerializer(
            [
                {
                    'date': log.date,
                    'is_completed': log.is_completed,
                    'completion_percent': _get_completion_percent(log),
                }
                for log in logs
            ],
            many=True,
        )
        return success_response(serializer.data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return success_response(None, '비밀번호가 변경되었습니다.')


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
