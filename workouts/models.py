from django.db import models
from django.conf import settings
from exercises.models import Exercise

class DailyLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField(auto_now_add=True)
    is_completed = models.BooleanField(default=False, help_text="오늘의 운동(루틴) 완료 여부")

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.email} - {self.date} (완료: {self.is_completed})"

class WorkoutSet(models.Model):
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='sets')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    set_number = models.IntegerField(help_text="몇 번째 세트인지")
    weight = models.FloatField(help_text="실제 든 무게(kg)")
    reps = models.IntegerField(help_text="실제 수행 횟수")
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['exercise', 'set_number']

    def __str__(self):
        return f"{self.daily_log.date} - {self.exercise.name} {self.set_number}세트"