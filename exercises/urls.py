from django.urls import path
from .views import ExerciseListView, AdminExerciseView

urlpatterns = [
    # 목표 주소: GET /catalog/exercises/
    path('exercises/', ExerciseListView.as_view(), name='exercise_list'),
    path('admin/exercises/', AdminExerciseView.as_view(), name='admin_exercises'),
]
