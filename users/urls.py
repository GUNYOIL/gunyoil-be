from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView

from .views import (
    CustomTokenObtainPairView,
    DashboardView,
    GrassView,
    OnboardingCompleteView,
    OnboardingDraftView,
    PasswordChangeView,
    SignupView,
    UserProfileView,
)


urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='logout'),
    path('me/', UserProfileView.as_view(), name='me'),
    path('me/profile/', UserProfileView.as_view(), name='profile_update'),
    path('me/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('me/grass/', GrassView.as_view(), name='grass'),
    path('me/password/', PasswordChangeView.as_view(), name='password_change'),
    path('me/onboarding/draft/', OnboardingDraftView.as_view(), name='onboarding_draft'),
    path('me/onboarding/complete/', OnboardingCompleteView.as_view(), name='onboarding_complete'),
]
