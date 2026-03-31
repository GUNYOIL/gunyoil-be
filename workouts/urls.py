from django.urls import path
from .views import WorkoutHistoryView

urlpatterns = [
    # 잔디 데이터를 가져올 주소: GET /me/workouts/history/
    path('history/', WorkoutHistoryView.as_view(), name='workout_history'),
]