from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from config.api import error_response, success_response
from diet.models import ProteinLog
from routines.models import Routine
from users.models import Announcement, Inquiry
from workouts.models import DailyLog
from workouts.serializers import DailyLogSerializer, TodayLogSerializer

from .push_notifications import (
    send_push_notification,
    send_lunch_reminders,
    send_breakfast_reminders,
    send_dinner_reminders,
    send_exercise_reminders,
)
from .serializers import (
    CustomTokenObtainPairSerializer,
    DashboardSerializer,
    GrassEntrySerializer,
    OnboardingCompleteSerializer,
    PasswordChangeSerializer,
    PushTokenSerializer,
    RunLunchReminderSerializer,
    RunBreakfastReminderSerializer,
    RunDinnerReminderSerializer,
    RunExerciseReminderSerializer,
    TestPushNotificationSerializer,
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


def _get_active_routine_weekdays(user):
    routines = Routine.objects.filter(user=user).prefetch_related('details')
    return {
        routine.day_of_week
        for routine in routines
        if routine.details.exists()
    }


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
        today = timezone.localdate()
        start_date = today - timedelta(days=364)
        logs = DailyLog.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today,
        ).prefetch_related('sets')
        logs_by_date = {log.date: log for log in logs}
        active_weekdays = _get_active_routine_weekdays(request.user)

        serializer = GrassEntrySerializer(
            [
                {
                    'date': date,
                    'is_completed': logs_by_date[date].is_completed if date in logs_by_date else False,
                    'completion_percent': _get_completion_percent(logs_by_date[date]) if date in logs_by_date else 0,
                    'is_rest_day': date.weekday() not in active_weekdays,
                }
                for date in (start_date + timedelta(days=offset) for offset in range(365))
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


class PushTokenView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PushTokenSerializer

    @extend_schema(
        summary='푸시 토큰 등록',
        request=PushTokenSerializer,
        responses={200: inline_serializer(
            name='PushTokenResponse',
            fields={
                'id': serializers.IntegerField(),
                'token': serializers.CharField(),
                'device_type': serializers.CharField(),
                'is_active': serializers.BooleanField(),
            },
        )},
    )
    def post(self, request):
        serializer = PushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        push_token, _ = request.user.push_tokens.update_or_create(
            token=serializer.validated_data['token'],
            defaults={
                'device_type': serializer.validated_data.get('device_type', 'web'),
                'is_active': True,
            },
        )

        return success_response(
            {
                'id': push_token.id,
                'token': push_token.token,
                'device_type': push_token.device_type,
                'is_active': push_token.is_active,
            },
            '푸시 토큰이 등록되었습니다.',
        )

    @extend_schema(
        summary='푸시 토큰 삭제',
        request=PushTokenSerializer,
        responses={200: OpenApiResponse(description='토큰 삭제 완료')},
    )
    def delete(self, request):
        serializer = PushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = request.user.push_tokens.filter(token=serializer.validated_data['token']).update(is_active=False)
        if not updated:
            return error_response('Push token not found.', status_code=status.HTTP_404_NOT_FOUND)

        return success_response(None, '푸시 토큰이 비활성화되었습니다.')


class PushNotificationTestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TestPushNotificationSerializer

    @extend_schema(
        summary='?몄떆 ?뚯넚 ?뚯뒪??',
        request=TestPushNotificationSerializer,
        responses={200: inline_serializer(
            name='PushNotificationTestResponse',
            fields={
                'token': serializers.CharField(),
                'message_id': serializers.CharField(),
            },
        )},
    )
    def post(self, request):
        serializer = TestPushNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get('token')
        if not token:
            push_token = request.user.push_tokens.filter(is_active=True).order_by('-updated_at', '-id').first()
            if not push_token:
                return error_response('Active push token not found.', status_code=status.HTTP_404_NOT_FOUND)
            token = push_token.token

        message_id = send_push_notification(
            token=token,
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            data={'type': 'test'},
        )

        return success_response(
            {
                'token': token,
                'message_id': message_id,
            },
            '?몄떆 ?뚯넚 ?뚯뒪?몄뿉 ?깃났?덉뒿?덈떎.',
        )


class AdminLunchReminderRunView(APIView):
    permission_classes = [IsAdminUser]
    serializer_class = RunLunchReminderSerializer

    @extend_schema(
        summary='점심 푸시 알림 수동 실행',
        request=RunLunchReminderSerializer,
        responses={200: inline_serializer(
            name='AdminLunchReminderRunResponse',
            fields={
                'date': serializers.DateField(),
                'target_count': serializers.IntegerField(),
                'success_count': serializers.IntegerField(),
                'failure_count': serializers.IntegerField(),
            },
        )},
    )
    def post(self, request):
        serializer = RunLunchReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        summary = send_lunch_reminders(target_date=serializer.validated_data.get('date'))
        return success_response(summary, '점심 푸시 알림 실행이 완료되었습니다.')


class AdminBreakfastReminderRunView(APIView):
    permission_classes = [IsAdminUser]
    serializer_class = RunBreakfastReminderSerializer

    @extend_schema(
        summary='아침 푸시 알림 수동 실행',
        request=RunBreakfastReminderSerializer,
        responses={200: inline_serializer(
            name='AdminBreakfastReminderRunResponse',
            fields={
                'date': serializers.DateField(),
                'target_count': serializers.IntegerField(),
                'success_count': serializers.IntegerField(),
                'failure_count': serializers.IntegerField(),
            },
        )},
    )
    def post(self, request):
        serializer = RunBreakfastReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        summary = send_breakfast_reminders(target_date=serializer.validated_data.get('date'))
        return success_response(summary, '아침 푸시 알림 실행이 완료되었습니다.')


class AdminDinnerReminderRunView(APIView):
    permission_classes = [IsAdminUser]
    serializer_class = RunDinnerReminderSerializer

    @extend_schema(
        summary='저녁 푸시 알림 수동 실행',
        request=RunDinnerReminderSerializer,
        responses={200: inline_serializer(
            name='AdminDinnerReminderRunResponse',
            fields={
                'date': serializers.DateField(),
                'target_count': serializers.IntegerField(),
                'success_count': serializers.IntegerField(),
                'failure_count': serializers.IntegerField(),
            },
        )},
    )
    def post(self, request):
        serializer = RunDinnerReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        summary = send_dinner_reminders(target_date=serializer.validated_data.get('date'))
        return success_response(summary, '저녁 푸시 알림 실행이 완료되었습니다.')


class AdminExerciseReminderRunView(APIView):
    permission_classes = [IsAdminUser]
    serializer_class = RunExerciseReminderSerializer

    @extend_schema(
        summary='운동 푸시 알림 수동 실행',
        request=RunExerciseReminderSerializer,
        responses={200: inline_serializer(
            name='AdminExerciseReminderRunResponse',
            fields={
                'date': serializers.DateField(),
                'target_count': serializers.IntegerField(),
                'success_count': serializers.IntegerField(),
                'failure_count': serializers.IntegerField(),
            },
        )},
    )
    def post(self, request):
        serializer = RunExerciseReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        summary = send_exercise_reminders(target_date=serializer.validated_data.get('date'))
        return success_response(summary, '운동 푸시 알림 실행이 완료되었습니다.')



class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='관리자 로그인',
        description='고정 관리자 계정으로 로그인해 토큰을 발급받습니다.',
        request=inline_serializer(
            name='AdminLoginRequest',
            fields={
                'username': serializers.CharField(),
                'password': serializers.CharField(),
            },
        ),
        responses={200: inline_serializer(
            name='AdminLoginResponse',
            fields={
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
            },
        )},
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if username == 'admin' and password == 'iamhelchang':
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import RefreshToken

            User = get_user_model()
            admin_user, created = User.objects.get_or_create(email='admin@gunyoil.com')
            if created:
                admin_user.set_password('iamhelchang')
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()

            refresh = RefreshToken.for_user(admin_user)
            return success_response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                '관리자 로그인 성공',
            )
        return error_response('Invalid credentials', status_code=status.HTTP_401_UNAUTHORIZED)


class AnnouncementListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='유저용 공지 조회',
        description='선택된 공지가 있으면 그 공지 1개만, 없으면 최신 공지 1개만 반환합니다.',
        responses={200: inline_serializer(
            name='AnnouncementListResponse',
            fields={
                'id': serializers.IntegerField(),
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'is_selected_for_users': serializers.BooleanField(),
                'created_at': serializers.DateTimeField(),
            },
            many=True,
        )},
    )
    def get(self, request):
        selected_announcement = Announcement.objects.filter(is_selected_for_users=True).first()
        if selected_announcement:
            announcements = [selected_announcement]
        else:
            latest_announcement = Announcement.objects.order_by('-created_at', '-id').first()
            announcements = [latest_announcement] if latest_announcement else []

        data = [
            {
                'id': announcement.id,
                'title': announcement.title,
                'content': announcement.content,
                'is_selected_for_users': announcement.is_selected_for_users,
                'created_at': announcement.created_at,
            }
            for announcement in announcements
        ]
        return success_response(data)


class AdminAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='공지사항 등록 (관리자)',
        request=inline_serializer(
            name='CreateAnnouncementRequest',
            fields={
                'title': serializers.CharField(),
                'content': serializers.CharField(),
            },
        ),
        responses={200: inline_serializer(
            name='CreateAnnouncementResponse',
            fields={
                'id': serializers.IntegerField(),
                'is_selected_for_users': serializers.BooleanField(),
            },
        )},
    )
    def post(self, request):
        title = request.data.get('title')
        content = request.data.get('content')
        if title and content:
            announcement = Announcement.objects.create(title=title, content=content)
            return success_response(
                {
                    'id': announcement.id,
                    'is_selected_for_users': announcement.is_selected_for_users,
                },
                '공지사항이 작성되었습니다.',
            )
        return error_response('입력값이 부족합니다.')


class AdminAnnouncementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='공지 선택 또는 삭제 (관리자)',
        request=inline_serializer(
            name='UpdateAnnouncementSelectionRequest',
            fields={
                'is_selected_for_users': serializers.BooleanField(),
            },
        ),
        responses={200: OpenApiResponse(description='선택 또는 삭제 완료')},
    )
    def patch(self, request, pk):
        if 'is_selected_for_users' not in request.data:
            return error_response('is_selected_for_users is required.')

        try:
            announcement = Announcement.objects.get(id=pk)
        except Announcement.DoesNotExist:
            return error_response('Announcement not found.', status_code=status.HTTP_404_NOT_FOUND)

        is_selected_for_users = bool(request.data.get('is_selected_for_users'))
        if is_selected_for_users:
            Announcement.objects.exclude(id=announcement.id).update(is_selected_for_users=False)

        announcement.is_selected_for_users = is_selected_for_users
        announcement.save(update_fields=['is_selected_for_users'])
        return success_response(
            {
                'id': announcement.id,
                'is_selected_for_users': announcement.is_selected_for_users,
            },
            '공지 선택 상태가 변경되었습니다.',
        )

    def delete(self, request, pk):
        Announcement.objects.filter(id=pk).delete()
        return success_response(None, '삭제했습니다.')


class InquiryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='내 문의 목록 조회 (사용자)',
        responses={200: inline_serializer(
            name='UserInquiryListResponse',
            fields={
                'id': serializers.IntegerField(),
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'reply_email': serializers.EmailField(allow_null=True),
                'status': serializers.CharField(),
                'created_at': serializers.DateTimeField(),
            },
            many=True,
        )},
    )
    def get(self, request):
        inquiries = Inquiry.objects.filter(user=request.user).order_by('-created_at', '-id')
        data = [
            {
                'id': inquiry.id,
                'title': inquiry.title,
                'content': inquiry.content,
                'reply_email': inquiry.reply_email,
                'status': inquiry.status,
                'created_at': inquiry.created_at,
            }
            for inquiry in inquiries
        ]
        return success_response(data)

    @extend_schema(
        summary='문의사항 접수 (사용자)',
        request=inline_serializer(
            name='CreateInquiryRequest',
            fields={
                'title': serializers.CharField(),
                'content': serializers.CharField(),
                'email': serializers.EmailField(),
            },
        ),
        responses={200: inline_serializer(
            name='CreateInquiryResponse',
            fields={'id': serializers.IntegerField()},
        )},
    )
    def post(self, request):
        title = request.data.get('title')
        content = request.data.get('content')
        reply_email = request.data.get('email')

        if title and content:
            inquiry = Inquiry.objects.create(
                user=request.user,
                title=title,
                content=content,
                reply_email=reply_email,
            )
            return success_response({'id': inquiry.id}, '문의가 접수되었습니다.')
        return error_response('제목과 내용을 입력해주세요.')


class AdminInquiryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='전체 문의 목록 조회 (관리자)',
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
            many=True,
        )},
    )
    def get(self, request):
        inquiries = Inquiry.objects.all().select_related('user')
        data = [
            {
                'id': inquiry.id,
                'user_email': inquiry.user.email,
                'reply_email': inquiry.reply_email,
                'title': inquiry.title,
                'content': inquiry.content,
                'status': inquiry.status,
                'created_at': inquiry.created_at,
            }
            for inquiry in inquiries
        ]
        return success_response(data)


class AdminInquiryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='문의 상태 변경 (관리자)',
        request=inline_serializer(
            name='UpdateInquiryStatusRequest',
            fields={
                'status': serializers.CharField(),
            },
        ),
        responses={200: OpenApiResponse(description='상태 변경 완료')},
    )
    def patch(self, request, pk):
        status_val = request.data.get('status')
        if status_val in ['PENDING', 'RESOLVED']:
            Inquiry.objects.filter(id=pk).update(status=status_val)
            return success_response(None, '상태가 변경되었습니다.')
        return error_response('잘못된 상태값입니다.')
