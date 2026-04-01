from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Exercise


User = get_user_model()


class ExerciseApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='exercise@example.com', password='password123')
        self.client.force_authenticate(self.user)
        Exercise.objects.create(name='Bench Press', category='CHEST', target_muscle='upper chest')
        Exercise.objects.create(name='Lat Pulldown', category='BACK', target_muscle='lats')

    def test_filter_exercises_by_target_muscle(self):
        response = self.client.get(f"{reverse('exercise_list')}?target_muscle=lat")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Lat Pulldown')

    def test_filter_exercises_by_search(self):
        response = self.client.get(f"{reverse('exercise_list')}?search=bench")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Bench Press')
