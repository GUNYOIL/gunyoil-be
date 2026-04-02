from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import MealLog, ProteinLog, SchoolMealSelectionLog


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


class MealLogSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='meal_type')
    type_label = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = MealLog
        fields = [
            'id',
            'date',
            'type',
            'type_label',
            'name',
            'calories',
            'protein',
            'carbs',
            'fat',
            'memo',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MealLogCreateSerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(choices=MealLog.MealType.choices, source='meal_type')
    date = serializers.DateField(required=False)

    class Meta:
        model = MealLog
        fields = ['date', 'type', 'name', 'calories', 'protein', 'carbs', 'fat', 'memo']

    def validate_calories(self, value):
        if value < 0:
            raise serializers.ValidationError('calories must be 0 or greater.')
        return value

    def _validate_non_negative_decimal(self, value, field_name):
        if value < Decimal('0'):
            raise serializers.ValidationError(f'{field_name} must be 0 or greater.')
        return value

    def validate_protein(self, value):
        return self._validate_non_negative_decimal(value, 'protein')

    def validate_carbs(self, value):
        return self._validate_non_negative_decimal(value, 'carbs')

    def validate_fat(self, value):
        return self._validate_non_negative_decimal(value, 'fat')

    def create(self, validated_data):
        validated_data.setdefault('date', timezone.localdate())
        return MealLog.objects.create(**validated_data)


class MealOverviewSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_calories = serializers.IntegerField()
    total_protein = serializers.DecimalField(max_digits=6, decimal_places=1)
    total_carbs = serializers.DecimalField(max_digits=6, decimal_places=1)
    total_fat = serializers.DecimalField(max_digits=6, decimal_places=1)
    meals = MealLogSerializer(many=True)


class SchoolMealSelectionItemSerializer(serializers.Serializer):
    menu_name = serializers.CharField(max_length=100)
    selection = serializers.ChoiceField(choices=SchoolMealSelectionLog.SelectionType.choices)
    estimated_protein_grams = serializers.DecimalField(max_digits=6, decimal_places=1)
    final_protein_grams = serializers.DecimalField(max_digits=6, decimal_places=1)

    def validate_estimated_protein_grams(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError('estimated_protein_grams must be 0 or greater.')
        return value

    def validate_final_protein_grams(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError('final_protein_grams must be 0 or greater.')
        return value


class SchoolMealSelectionSaveSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    meal_type = serializers.ChoiceField(choices=SchoolMealSelectionLog.MealType.choices)
    items = SchoolMealSelectionItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('items must not be empty.')
        return value


class SchoolMealSelectionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolMealSelectionLog
        fields = [
            'id',
            'date',
            'meal_type',
            'menu_name',
            'selection',
            'estimated_protein_grams',
            'final_protein_grams',
            'created_at',
        ]
