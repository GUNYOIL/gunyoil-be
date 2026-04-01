from django.contrib import admin

from .models import MealLog, ProteinLog


@admin.register(ProteinLog)
class ProteinLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'amount', 'log_type', 'created_at']
    list_filter = ['log_type', 'date']
    search_fields = ['user__email', 'note']


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'meal_type', 'name', 'calories', 'created_at']
    list_filter = ['meal_type', 'date']
    search_fields = ['user__email', 'name', 'memo']
