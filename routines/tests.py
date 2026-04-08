from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from exercises.models import Exercise
from routines.models import Routine


User = get_user_model()


class UserRoutineApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='routine@example.com', password='Password123!')
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(
            code='barbell-bench-press',
            name='바벨 벤치프레스',
            category='strength',
            target_muscle='chest',
        )

    def test_put_routines_without_trailing_slash_saves_routines(self):
        payload = [
            {
                'day_of_week': 0,
                'details': [
                    {
                        'exercise': self.exercise.id,
                        'target_weight': 40,
                        'target_reps': 10,
                        'target_sets': 3,
                        'order': 0,
                    }
                ],
            }
        ]

        response = self.client.put('/me/routines', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Routine.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Routine.objects.get(user=self.user, day_of_week=0).details.count(), 1)

    def test_get_routines_without_trailing_slash_returns_saved_routines(self):
        routine = Routine.objects.create(user=self.user, day_of_week=0)
        routine.details.create(
            exercise=self.exercise,
            target_weight=40,
            target_reps=10,
            target_sets=3,
            order=0,
        )

        response = self.client.get('/me/routines')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['day_of_week'], 0)
