from django.contrib import admin
from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'target_muscle', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'code', 'target_muscle')
