from django.db import models


class Exercise(models.Model):
    CATEGORY_CHOICES = (
        ('CHEST', '가슴'),
        ('BACK', '등'),
        ('LEGS', '하체'),
        ('SHOULDERS', '어깨'),
        ('ARMS', '팔'),
        ('ABS', '코어'),
        ('CARDIO', '유산소'),
    )

    code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    target_muscle = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'[{self.get_category_display()}] {self.name}'
