from django.urls import path

from .views import (
    MealLogCreateView,
    MealLogDeleteView,
    MealView,
    ProteinLogCreateView,
    ProteinLogDeleteView,
    ProteinView,
)


urlpatterns = [
    path('protein', ProteinView.as_view(), name='protein_overview'),
    path('protein/logs', ProteinLogCreateView.as_view(), name='protein_log_create'),
    path('protein/logs/<int:log_id>/', ProteinLogDeleteView.as_view(), name='protein_log_delete'),
    path('meals', MealView.as_view(), name='meal_overview'),
    path('meals/logs', MealLogCreateView.as_view(), name='meal_log_create'),
    path('meals/logs/<int:meal_id>/', MealLogDeleteView.as_view(), name='meal_log_delete'),
]
