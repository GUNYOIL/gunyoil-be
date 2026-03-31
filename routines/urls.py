from django.urls import path
from .views import UserRoutineView

urlpatterns = [
    # 주소: /me/routines/
    path('routines/', UserRoutineView.as_view(), name='user_routines'),
]
