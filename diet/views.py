from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api import error_response, success_response
from .models import MealLog, ProteinLog, SchoolMealSelectionLog
from .serializers import (
    MealLogCreateSerializer,
    MealLogSerializer,
    MealOverviewSerializer,
    ProteinLogCreateSerializer,
    ProteinLogSerializer,
    ProteinOverviewSerializer,
    SchoolMealSelectionLogSerializer,
    SchoolMealSelectionSaveSerializer,
)
from .services import SchoolMealConfigError, fetch_school_lunch, transform_school_meal_for_app


DEFAULT_PROTEIN_MULTIPLIER = Decimal('1.6')


def _quantize(value):
    return value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def _get_target_amount(user):
    if not user.weight:
        return None
    return _quantize(Decimal(str(user.weight)) * DEFAULT_PROTEIN_MULTIPLIER)


def _get_request_date(request):
    date_value = request.query_params.get('date')
    if not date_value:
        return timezone.localdate(), None

    try:
        return timezone.datetime.strptime(date_value, '%Y-%m-%d').date(), None
    except ValueError:
        return None, error_response('date must be in YYYY-MM-DD format.', code='invalid_date', status_code=status.HTTP_400_BAD_REQUEST)


def _get_meal_type(request):
    meal_type = request.query_params.get('meal_type', 'breakfast').lower()
    if meal_type not in {'breakfast', 'lunch', 'dinner'}:
        return None, error_response(
            'meal_type must be one of breakfast, lunch, dinner.',
            code='invalid_meal_type',
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return meal_type, None


class ProteinView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        logs = ProteinLog.objects.filter(user=request.user, date=today).order_by('-created_at', '-id')
        consumed_amount = _quantize(sum((log.amount for log in logs), Decimal('0.0')))
        target_amount = _get_target_amount(request.user)

        remaining_amount = None
        progress_percent = 0
        is_target_completed = False

        if target_amount is not None and target_amount > 0:
            remaining_amount = _quantize(max(target_amount - consumed_amount, Decimal('0.0')))
            progress_percent = min(int((consumed_amount / target_amount) * 100), 100)
            is_target_completed = consumed_amount >= target_amount

        serializer = ProteinOverviewSerializer(
            {
                'date': today,
                'target_amount': target_amount,
                'consumed_amount': consumed_amount,
                'remaining_amount': remaining_amount,
                'progress_percent': progress_percent,
                'is_target_completed': is_target_completed,
                'logs': logs,
            }
        )
        return success_response(serializer.data)


class ProteinLogCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProteinLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        protein_log = serializer.save(user=request.user)
        return success_response(ProteinLogSerializer(protein_log).data, '단백질 로그가 추가되었습니다.', status.HTTP_201_CREATED)


class ProteinLogDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, log_id):
        try:
            protein_log = ProteinLog.objects.get(id=log_id, user=request.user)
        except ProteinLog.DoesNotExist:
            return error_response('Protein log not found.', code='protein_log_not_found', status_code=status.HTTP_404_NOT_FOUND)

        protein_log.delete()
        return success_response(None, '단백질 로그가 삭제되었습니다.')


class MealView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date, error_response_obj = _get_request_date(request)
        if error_response_obj:
            return error_response_obj

        meals = MealLog.objects.filter(user=request.user, date=target_date).order_by('-created_at', '-id')
        serializer = MealOverviewSerializer(
            {
                'date': target_date,
                'total_calories': sum(meal.calories for meal in meals),
                'total_protein': _quantize(sum((meal.protein for meal in meals), Decimal('0.0'))),
                'total_carbs': _quantize(sum((meal.carbs for meal in meals), Decimal('0.0'))),
                'total_fat': _quantize(sum((meal.fat for meal in meals), Decimal('0.0'))),
                'meals': meals,
            }
        )
        return success_response(serializer.data)


class MealLogCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MealLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal_log = serializer.save(user=request.user)
        return success_response(MealLogSerializer(meal_log).data, '식단 로그가 추가되었습니다.', status.HTTP_201_CREATED)


class MealLogDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, meal_id):
        try:
            meal_log = MealLog.objects.get(id=meal_id, user=request.user)
        except MealLog.DoesNotExist:
            return error_response('Meal log not found.', code='meal_log_not_found', status_code=status.HTTP_404_NOT_FOUND)

        meal_log.delete()
        return success_response(None, '식단 로그가 삭제되었습니다.')


class SchoolLunchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date, error_response_obj = _get_request_date(request)
        if error_response_obj:
            return error_response_obj

        meal_type, meal_type_error = _get_meal_type(request)
        if meal_type_error:
            return meal_type_error

        try:
            lunch = fetch_school_lunch(target_date, meal_type=meal_type)
        except SchoolMealConfigError as exc:
            return error_response(str(exc), code='school_meal_config_error', status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as exc:
            return error_response(str(exc), code='school_meal_fetch_failed', status_code=status.HTTP_502_BAD_GATEWAY)

        transformed_meal = transform_school_meal_for_app(lunch, meal_type)

        return success_response(
            {
                'date': transformed_meal['date'],
                'school': {
                    'education_office_code': settings.NEIS_ATPT_CODE,
                    'school_code': settings.NEIS_SCHOOL_CODE,
                },
                'meal_type': transformed_meal['meal_type'],
                'meal_type_label': transformed_meal['meal_type_label'],
                'menus': transformed_meal['menus'],
                'estimated_total_protein': transformed_meal['estimated_total_protein'],
                'school_total_protein': transformed_meal['school_total_protein'],
                'calories': transformed_meal['calories'],
                'nutrition_info': transformed_meal['nutrition_info'],
            }
        )


class SchoolLunchSelectionSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SchoolMealSelectionSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_date = serializer.validated_data.get('date', timezone.localdate())
        meal_type = serializer.validated_data['meal_type']
        items = serializer.validated_data['items']

        SchoolMealSelectionLog.objects.filter(
            user=request.user,
            date=target_date,
            meal_type=meal_type,
        ).delete()

        selection_logs = []
        total_protein = Decimal('0.0')

        for item in items:
            selection_log = SchoolMealSelectionLog.objects.create(
                user=request.user,
                date=target_date,
                meal_type=meal_type,
                menu_name=item['menu_name'],
                selection=item['selection'],
                estimated_protein_grams=item['estimated_protein_grams'],
                final_protein_grams=item['final_protein_grams'],
            )
            selection_logs.append(selection_log)
            total_protein += item['final_protein_grams']

        ProteinLog.objects.filter(
            user=request.user,
            date=target_date,
            log_type=ProteinLog.LogType.MEAL,
            note=f'school-lunch:{meal_type}',
        ).delete()

        protein_log = ProteinLog.objects.create(
            user=request.user,
            date=target_date,
            amount=_quantize(total_protein),
            log_type=ProteinLog.LogType.MEAL,
            note=f'school-lunch:{meal_type}',
        )

        return success_response(
            {
                'date': target_date,
                'meal_type': meal_type,
                'total_protein': str(protein_log.amount),
                'protein_log_id': protein_log.id,
                'items': SchoolMealSelectionLogSerializer(selection_logs, many=True).data,
            },
            '급식 기록이 저장되었습니다.',
            status.HTTP_201_CREATED,
        )
