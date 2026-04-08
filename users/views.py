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

from users.models import Announcement, Inquiry
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers

class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="어드민 로그인",
        description="고정된 어드민 계정(admin)으로 로그인하여 토큰을 발급받습니다.",
        request=inline_serializer(
            name='AdminLoginRequest',
            fields={
                'username': serializers.CharField(),
                'password': serializers.CharField(),
            }
        ),
        responses={200: inline_serializer(
            name='AdminLoginResponse',
            fields={
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
            }
        )}
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if username == 'admin' and password == 'iamhelchang':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_user, created = User.objects.get_or_create(email='admin@gunyoil.com')
            if created:
                admin_user.set_password('iamhelchang')
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(admin_user)
            return success_response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, '어드민 로그인 성공')
        return error_response('Invalid credentials', status_code=status.HTTP_401_UNAUTHORIZED)

class AnnouncementListView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="공지사항 전체 조회",
        description="등록된 모든 공지사항을 불러옵니다.",
        responses={200: inline_serializer(
            name='AnnouncementListResponse',
            fields={
                'id': serializers.IntegerField(),
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'created_at': serializers.DateTimeField(),
            },
            many=True
        )}
    )
    def get(self, request):
        announcements = Announcement.objects.all()
        data = [{'id': a.id, 'title': a.title, 'content': a.content, 'created_at': a.created_at} for a in announcements]
        return success_response(data)

class AdminAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="공지사항 등록 (어드민)",
        request=inline_serializer(
            name='CreateAnnouncementRequest',
            fields={
                'title': serializers.CharField(),
                'content': serializers.CharField(),
            }
        )
    )
    def post(self, request):
        title = request.data.get('title')
        content = request.data.get('content')
        if title and content:
            a = Announcement.objects.create(title=title, content=content)
            return success_response({'id': a.id}, '공지가 작성되었습니다.')
        return error_response('입력값이 부족합니다.')
        
class AdminAnnouncementDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(summary="공지사항 삭제 (어드민)")
    def delete(self, request, pk):
        Announcement.objects.filter(id=pk).delete()
        return success_response(None, '삭제되었습니다.')

class InquiryView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="문의사항 접수 (사용자)",
        request=inline_serializer(
            name='CreateInquiryRequest',
            fields={
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'email': serializers.EmailField(),
            }
        )
    )
    def post(self, request):
        title = request.data.get('title')
        content = request.data.get('content')
        reply_email = request.data.get('email') # 프론트에서 넘어올 필드명에 맞춤 (답변 이메일)
        
        if title and content:
            i = Inquiry.objects.create(
                user=request.user, 
                title=title,
                content=content,
                reply_email=reply_email
            )
            return success_response({'id': i.id}, '문의가 접수되었습니다.')
        return error_response('제목과 내용을 입력하세요.')

class AdminInquiryView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="모든 사용자 문의내역 조회 (어드민)",
        responses={200: inline_serializer(
            name='AdminInquiryListResponse',
            fields={
                'id': serializers.IntegerField(),
                'user_email': serializers.EmailField(),
                'reply_email': serializers.EmailField(),
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'status': serializers.CharField(),
                'created_at': serializers.DateTimeField(),
            },
            many=True
        )}
    )
    def get(self, request):
        inquiries = Inquiry.objects.all().select_related('user')
        data = [{
            'id': i.id,
            'user_email': i.user.email,
            'reply_email': i.reply_email,
            'title': i.title,
            'content': i.content,
            'status': i.status,
            'created_at': i.created_at
        } for i in inquiries]
        return success_response(data)

class AdminInquiryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="문의사항 답변/해결 상태 변경 (어드민)",
        request=inline_serializer(
            name='UpdateInquiryStatusRequest',
            fields={
                'status': serializers.CharField(),
            }
        )
    )
    def patch(self, request, pk):
        status_val = request.data.get('status')
        if status_val in ['PENDING', 'RESOLVED']:
            Inquiry.objects.filter(id=pk).update(status=status_val)
            return success_response(None, '상태가 변경되었습니다.')
        return error_response('잘못된 상태값입니다.')
