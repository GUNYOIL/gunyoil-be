from django.db import models
from django.conf import settings
from exercises.models import Exercise

class Routine(models.Model):
    DAY_CHOICES = (
        (0, '월요일'),
        (1, '화요일'),
        (2, '수요일'),
        (3, '목요일'),
        (4, '금요일'),
        (5, '토요일'),
        (6, '일요일'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routines')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    
    class Meta:
        unique_together = ('user', 'day_of_week')

    def __str__(self):
        return f"{self.user.email} 님의 {self.get_day_of_week_display()} 루틴"

class RoutineDetail(models.Model):
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name='details')
    
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    
    target_weight = models.FloatField(help_text="목표 무게(kg)")
    target_reps = models.IntegerField(help_text="목표 횟수")
    target_sets = models.IntegerField(help_text="목표 세트 수")
    order = models.IntegerField(default=0, help_text="해당 요일의 운동 진행 순서") 

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.routine} - {self.exercise.name} ({self.target_weight}kg x {self.target_reps}회 {self.target_sets}세트)"
