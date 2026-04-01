from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import ProteinLog


class ProteinLogSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='log_type')
    type_label = serializers.CharField(source='get_log_type_display', read_only=True)

    class Meta:
        model = ProteinLog
        fields = ['id', 'date', 'amount', 'type', 'type_label', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProteinLogCreateSerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(choices=ProteinLog.LogType.choices, source='log_type')
    date = serializers.DateField(required=False)

    class Meta:
        model = ProteinLog
        fields = ['date', 'amount', 'type', 'note']

    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('amount must be greater than 0.')
        return value

    def create(self, validated_data):
        validated_data.setdefault('date', timezone.localdate())
        return ProteinLog.objects.create(**validated_data)


class ProteinOverviewSerializer(serializers.Serializer):
    date = serializers.DateField()
    target_amount = serializers.DecimalField(max_digits=6, decimal_places=1, allow_null=True)
    consumed_amount = serializers.DecimalField(max_digits=6, decimal_places=1)
    remaining_amount = serializers.DecimalField(max_digits=6, decimal_places=1, allow_null=True)
    progress_percent = serializers.IntegerField()
    is_target_completed = serializers.BooleanField()
    logs = ProteinLogSerializer(many=True)
