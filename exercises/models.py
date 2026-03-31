from django.db import models

class Exercise(models.Model):
    CATEGORY_CHOICES = (
        ('CHEST', '가슴'),
        ('BACK', '등'),
        ('LEGS', '하체'),
        ('SHOULDERS', '어깨'),
        ('ARMS', '팔'),
        ('ABS', '복근'),
        ('CARDIO', '유산소'),
    )

    name = models.CharField(max_length=100) # 기구명/운동명 (예: 랫풀다운)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    target_muscle = models.CharField(max_length=50, blank=True) # 세부 타겟 부위 (예: 광배근)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"
