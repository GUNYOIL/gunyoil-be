from django.contrib import admin
from .models import User, UserPushToken, Announcement, Inquiry

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email',)

@admin.register(UserPushToken)
class UserPushTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'updated_at')
    list_filter = ('is_active', 'device_type')
    search_fields = ('user__email', 'token')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_selected_for_users', 'created_at')

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'created_at')
    list_filter = ('status',)
