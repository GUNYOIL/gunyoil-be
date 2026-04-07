from django.urls import path

from .views import TodayWorkoutSetCreateView, TodayWorkoutView, WorkoutHistoryView


urlpatterns = [
    path('history/', WorkoutHistoryView.as_view(), name='workout_history'),
    path('today/', TodayWorkoutView.as_view(), name='workout_today'),
    path('today/sets/', TodayWorkoutSetCreateView.as_view(), name='workout_set_update'),
    path('today/sets', TodayWorkoutSetCreateView.as_view()),
]
