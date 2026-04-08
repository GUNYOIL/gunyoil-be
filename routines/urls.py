from django.urls import path

from .views import UserRoutineView


urlpatterns = [
    path('routines', UserRoutineView.as_view(), name='user_routines_no_slash'),
    path('routines/', UserRoutineView.as_view(), name='user_routines'),
]
