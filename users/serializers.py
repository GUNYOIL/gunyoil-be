from rest_framework import serializers
from django.contrib.auth import get_user_model

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
            onboarding_completed=validated_data.get('onboarding_completed', False)
        )
        return user

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        return {
            'access': data['access'],
            'refresh': data['refresh']
        }
