from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .views import SignupView, UserProfileView, OnboardingCompleteView, CustomTokenObtainPairView

urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='logout'),
    path('me/', UserProfileView.as_view(), name='me'),
    path('me/profile/', UserProfileView.as_view(), name='profile_update'),
    path('me/onboarding/complete/', OnboardingCompleteView.as_view(), name='onboarding_complete'),
]
