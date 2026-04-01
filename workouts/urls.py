from django.urls import path
from .views import WorkoutHistoryView, TodayWorkoutView, WorkoutSetUpdateView

urlpatterns = [
    path('history/', WorkoutHistoryView.as_view(), name='workout_history'),
    path('today/', TodayWorkoutView.as_view(), name='workout_today'),
    path('sets/<int:set_id>/', WorkoutSetUpdateView.as_view(), name='workout_set_update'),
]