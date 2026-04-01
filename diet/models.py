from django.conf import settings
from django.db import models


class ProteinLog(models.Model):
    class LogType(models.TextChoices):
        QUICK = 'quick', 'Quick Add'
        MANUAL = 'manual', 'Manual Input'
        MEAL = 'meal', 'Meal'
        SUPPLEMENT = 'supplement', 'Supplement'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='protein_logs',
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=6, decimal_places=1)
    log_type = models.CharField(
        max_length=20,
        choices=LogType.choices,
        default=LogType.QUICK,
    )
    note = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user.email} - {self.date} - {self.amount}g'


class MealLog(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = 'breakfast', 'Breakfast'
        LUNCH = 'lunch', 'Lunch'
        DINNER = 'dinner', 'Dinner'
        SNACK = 'snack', 'Snack'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meal_logs',
    )
    date = models.DateField()
    meal_type = models.CharField(
        max_length=20,
        choices=MealType.choices,
        default=MealType.BREAKFAST,
    )
    name = models.CharField(max_length=100)
    calories = models.PositiveIntegerField(default=0)
    protein = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    carbs = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    fat = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    memo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user.email} - {self.date} - {self.name}'
