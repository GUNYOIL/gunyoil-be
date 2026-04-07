import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from exercises.models import Exercise
from routines.models import Routine, RoutineDetail
from workouts.models import DailyLog


User = get_user_model()


class WorkoutApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='workout@example.com', password='password123')
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(name='Squat', category='LEGS', target_muscle='quads')
        routine = Routine.objects.create(user=self.user, day_of_week=datetime.date.today().weekday())
        RoutineDetail.objects.create(
            routine=routine,
            exercise=self.exercise,
            target_weight=100,
            target_reps=5,
            target_sets=2,
            order=1,
        )

    def test_save_today_set_via_post_endpoint(self):
        today_response = self.client.get(reverse('workout_today'))
        set_id = today_response.data['data']['sets'][0]['id']

        response = self.client.post(
            reverse('workout_set_update'),
            {
                'set_id': set_id,
                'weight': 105,
                'reps': 4,
                'is_completed': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['weight'], 105.0)
        self.assertTrue(response.data['data']['is_completed'])

    def test_get_today_workout_populates_sets_for_existing_empty_log(self):
        DailyLog.objects.create(user=self.user, is_completed=False)

        response = self.client.get(reverse('workout_today'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']['sets']), 2)
        self.assertTrue(all(item['id'] for item in response.data['data']['sets']))

    def test_save_today_workout_via_put_endpoint(self):
        today_response = self.client.get(reverse('workout_today'))
        first_set_id = today_response.data['data']['sets'][0]['id']
        second_set_id = today_response.data['data']['sets'][1]['id']

        response = self.client.put(
            reverse('workout_today'),
            {
                'is_completed': True,
                'sets': [
                    {
                        'set_id': first_set_id,
                        'weight': 110,
                        'reps': 5,
                        'is_completed': True,
                    },
                    {
                        'set_id': second_set_id,
                        'weight': 107.5,
                        'reps': 4,
                        'is_completed': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['data']['is_completed'])
        self.assertEqual(len(response.data['data']['sets']), 2)
        self.assertTrue(all(item['is_completed'] for item in response.data['data']['sets']))
