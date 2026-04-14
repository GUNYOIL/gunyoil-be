from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'gender', 'height', 'weight', 'goal', 'onboarding_completed']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            gender=validated_data.get('gender'),
            height=validated_data.get('height'),
            weight=validated_data.get('weight'),
            goal=validated_data.get('goal'),
            onboarding_completed=validated_data.get('onboarding_completed', False),
        )
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class GrassEntrySerializer(serializers.Serializer):
    date = serializers.DateField()
    is_completed = serializers.BooleanField()
    completion_percent = serializers.IntegerField()
    is_rest_day = serializers.BooleanField()


class OnboardingCompleteSerializer(serializers.Serializer):
    onboarding_completed = serializers.BooleanField()


class RecentWorkoutSerializer(serializers.Serializer):
    date = serializers.DateField()
    is_completed = serializers.BooleanField()


class DashboardProteinSerializer(serializers.Serializer):
    target_amount = serializers.DecimalField(max_digits=6, decimal_places=1, allow_null=True)
    consumed_amount = serializers.DecimalField(max_digits=6, decimal_places=1)
    progress_percent = serializers.IntegerField()
    is_target_completed = serializers.BooleanField()


class DashboardSerializer(serializers.Serializer):
    date = serializers.DateField()
    today_workout = serializers.DictField()
    protein = DashboardProteinSerializer()
    recent_workouts = RecentWorkoutSerializer(many=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        return {
            'access': data['access'],
            'refresh': data['refresh'],
        }


class PushTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    device_type = serializers.ChoiceField(choices=['web'], default='web', required=False)


class TestPushNotificationSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, default='근요일 테스트 알림')
    body = serializers.CharField(required=False, default='푸시 알림 테스트가 정상적으로 도착했습니다.')
    token = serializers.CharField(required=False, allow_blank=False)


class RunLunchReminderSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
