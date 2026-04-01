from django.contrib import admin

from .models import ProteinLog


@admin.register(ProteinLog)
class ProteinLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'amount', 'log_type', 'created_at']
    list_filter = ['log_type', 'date']
    search_fields = ['user__email', 'note']
