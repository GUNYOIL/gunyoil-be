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
    AdminLoginView,
    AnnouncementListView,
    AdminAnnouncementView,
    AdminAnnouncementDetailView,
    InquiryView,
    AdminInquiryView,
    AdminInquiryDetailView,
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
    
    path('auth/admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('announcements/', AnnouncementListView.as_view(), name='announcements'),
    path('admin/announcements/', AdminAnnouncementView.as_view(), name='admin_announcements'),
    path('admin/announcements/<int:pk>/', AdminAnnouncementDetailView.as_view(), name='admin_announcements_detail'),
    path('me/inquiries/', InquiryView.as_view(), name='me_inquiries'),
    path('admin/inquiries/', AdminInquiryView.as_view(), name='admin_inquiries'),
    path('admin/inquiries/<int:pk>/', AdminInquiryDetailView.as_view(), name='admin_inquiries_detail'),
]
