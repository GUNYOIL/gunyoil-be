from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from diet.models import ProteinLog
from exercises.models import Exercise
from routines.models import Routine, RoutineDetail
from workouts.models import DailyLog, WorkoutSet
from users.models import Inquiry


User = get_user_model()


class UserApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            onboarding_completed=True,
            weight=70,
        )
        self.client.force_authenticate(self.user)

    def _create_daily_log(self, date, is_completed):
        log = DailyLog.objects.create(user=self.user, is_completed=is_completed)
        DailyLog.objects.filter(id=log.id).update(date=date)
        log.refresh_from_db()
        return log

    def test_save_onboarding_draft(self):
        response = self.client.put(
            reverse('onboarding_draft'),
            {
                'gender': 'M',
                'height': 180,
                'weight': 78,
                'goal': 'muscle gain',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['height'], 180.0)
        self.user.refresh_from_db()
        self.assertFalse(self.user.onboarding_completed)

    def test_get_dashboard(self):
        today = timezone.localdate()
        exercise = Exercise.objects.create(name='Bench Press', category='CHEST', target_muscle='chest')
        routine = Routine.objects.create(user=self.user, day_of_week=today.weekday())
        RoutineDetail.objects.create(
            routine=routine,
            exercise=exercise,
            target_weight=60,
            target_reps=10,
            target_sets=2,
            order=1,
        )
        self._create_daily_log(today - timedelta(days=1), True)
        ProteinLog.objects.create(
            user=self.user,
            date=today,
            amount=Decimal('30.0'),
            log_type=ProteinLog.LogType.MEAL,
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertEqual(data['protein']['target_amount'], '112.0')
        self.assertEqual(data['protein']['consumed_amount'], '30.0')
        self.assertEqual(len(data['today_workout']['sets']), 2)
        self.assertEqual(len(data['recent_workouts']), 1)

    def test_get_grass(self):
        incomplete_log = self._create_daily_log(timezone.localdate() - timedelta(days=1), False)
        complete_log = self._create_daily_log(timezone.localdate(), True)
        exercise = Exercise.objects.create(name='Squat', category='LEGS', target_muscle='quads')
        WorkoutSet.objects.create(
            daily_log=incomplete_log,
            exercise=exercise,
            set_number=1,
            weight=60,
            reps=10,
            is_completed=False,
        )
        WorkoutSet.objects.create(
            daily_log=incomplete_log,
            exercise=exercise,
            set_number=2,
            weight=60,
            reps=10,
            is_completed=True,
        )
        WorkoutSet.objects.create(
            daily_log=complete_log,
            exercise=exercise,
            set_number=1,
            weight=60,
            reps=10,
            is_completed=True,
        )

        response = self.client.get(reverse('grass'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(response.data['data'][0]['completion_percent'], 50)
        self.assertEqual(response.data['data'][1]['completion_percent'], 100)

    def test_change_password(self):
        response = self.client.patch(
            reverse('password_change'),
            {
                'current_password': 'password123',
                'new_password': 'newpassword456',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword456'))

    def test_delete_me(self):
        response = self.client.delete(reverse('me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

    def test_patch_admin_inquiry_without_trailing_slash(self):
        inquiry = Inquiry.objects.create(
            user=self.user,
            title='문의',
            content='내용',
            reply_email='user@example.com',
        )

        response = self.client.patch(
            f'/admin/inquiries/{inquiry.id}',
            {'status': 'RESOLVED'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, 'RESOLVED')
