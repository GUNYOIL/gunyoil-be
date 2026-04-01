from django.urls import path

from .views import ProteinLogCreateView, ProteinLogDeleteView, ProteinView


urlpatterns = [
    path('protein', ProteinView.as_view(), name='protein_overview'),
    path('protein/logs', ProteinLogCreateView.as_view(), name='protein_log_create'),
    path('protein/logs/<int:log_id>/', ProteinLogDeleteView.as_view(), name='protein_log_delete'),
]
