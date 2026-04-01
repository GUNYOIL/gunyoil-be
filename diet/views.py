from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProteinLog
from .serializers import (
    ProteinLogCreateSerializer,
    ProteinLogSerializer,
    ProteinOverviewSerializer,
)


DEFAULT_PROTEIN_MULTIPLIER = Decimal('1.6')


def _quantize(value):
    return value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def _get_target_amount(user):
    if not user.weight:
        return None
    return _quantize(Decimal(str(user.weight)) * DEFAULT_PROTEIN_MULTIPLIER)


class ProteinView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        logs = ProteinLog.objects.filter(user=request.user, date=today).order_by('-created_at', '-id')
        consumed_amount = _quantize(
            sum((log.amount for log in logs), Decimal('0.0'))
        )
        target_amount = _get_target_amount(request.user)

        remaining_amount = None
        progress_percent = 0
        is_target_completed = False

        if target_amount is not None and target_amount > 0:
            remaining_amount = _quantize(max(target_amount - consumed_amount, Decimal('0.0')))
            progress_percent = min(
                int((consumed_amount / target_amount) * 100),
                100,
            )
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
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProteinLogCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProteinLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        protein_log = serializer.save(user=request.user)
        return Response(ProteinLogSerializer(protein_log).data, status=status.HTTP_201_CREATED)


class ProteinLogDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, log_id):
        try:
            protein_log = ProteinLog.objects.get(id=log_id, user=request.user)
        except ProteinLog.DoesNotExist:
            return Response({'detail': 'Protein log not found.'}, status=status.HTTP_404_NOT_FOUND)

        protein_log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
