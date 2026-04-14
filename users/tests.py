from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from diet.models import ProteinLog, SchoolMealSelectionLog
from exercises.models import Exercise
from routines.models import Routine, RoutineDetail
from users.models import Announcement, Inquiry, UserPushToken
from users.push_notifications import get_lunch_reminder_targets, send_lunch_reminders
from workouts.models import DailyLog, WorkoutSet


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
        for weekday in {
            timezone.localdate().weekday(),
            (timezone.localdate() - timedelta(days=1)).weekday(),
        }:
            routine = Routine.objects.create(user=self.user, day_of_week=weekday)
            RoutineDetail.objects.create(
                routine=routine,
                exercise=exercise,
                target_weight=60,
                target_reps=10,
                target_sets=2,
                order=1,
            )
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
        self.assertEqual(len(response.data['data']), 365)

        data_by_date = {entry['date']: entry for entry in response.data['data']}
        yesterday = str(timezone.localdate() - timedelta(days=1))
        today = str(timezone.localdate())
        two_days_ago = str(timezone.localdate() - timedelta(days=2))

        self.assertEqual(data_by_date[yesterday]['completion_percent'], 50)
        self.assertFalse(data_by_date[yesterday]['is_rest_day'])
        self.assertEqual(data_by_date[today]['completion_percent'], 100)
        self.assertFalse(data_by_date[today]['is_rest_day'])
        self.assertTrue(data_by_date[two_days_ago]['is_rest_day'])
        self.assertEqual(data_by_date[two_days_ago]['completion_percent'], 0)

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

    def test_register_push_token(self):
        response = self.client.post(
            '/me/push-tokens/',
            {
                'token': 'web-token-1',
                'device_type': 'web',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(UserPushToken.objects.filter(user=self.user, token='web-token-1', is_active=True).count(), 1)

    def test_delete_push_token_marks_token_inactive(self):
        push_token = UserPushToken.objects.create(user=self.user, token='web-token-1', device_type='web', is_active=True)

        response = self.client.delete(
            '/me/push-tokens/',
            {
                'token': push_token.token,
                'device_type': 'web',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        push_token.refresh_from_db()
        self.assertFalse(push_token.is_active)

    @patch('users.views.send_push_notification', return_value='projects/gunyoil/messages/test-message-id')
    def test_send_test_push_notification_with_saved_token(self, mocked_send):
        UserPushToken.objects.create(user=self.user, token='web-token-1', device_type='web', is_active=True)

        response = self.client.post(
            '/me/push-tokens/test/',
            {
                'title': '테스트 제목',
                'body': '테스트 본문',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['token'], 'web-token-1')
        self.assertEqual(response.data['data']['message_id'], 'projects/gunyoil/messages/test-message-id')
        mocked_send.assert_called_once_with(
            token='web-token-1',
            title='테스트 제목',
            body='테스트 본문',
            data={'type': 'test'},
        )

    def test_send_test_push_notification_without_saved_token_returns_404(self):
        response = self.client.post('/me/push-tokens/test/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])

    def test_get_lunch_reminder_targets_excludes_users_with_lunch_log(self):
        other_user = User.objects.create_user(email='other@example.com', password='password123')
        UserPushToken.objects.create(user=self.user, token='web-token-1', device_type='web', is_active=True)
        UserPushToken.objects.create(user=other_user, token='web-token-2', device_type='web', is_active=True)
        SchoolMealSelectionLog.objects.create(
            user=other_user,
            date=timezone.localdate(),
            meal_type='lunch',
            menu_name='돈까스',
            selection='medium',
            estimated_protein_grams='11.0',
            final_protein_grams='11.0',
        )

        targets = get_lunch_reminder_targets()

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].token, 'web-token-1')

    @patch('users.push_notifications.send_push_notifications')
    def test_send_lunch_reminders_deactivates_invalid_tokens(self, mocked_send_push_notifications):
        push_token = UserPushToken.objects.create(user=self.user, token='web-token-1', device_type='web', is_active=True)
        mocked_send_push_notifications.return_value = [
            {'token': push_token.token, 'success': False, 'error': 'NotRegistered'},
        ]

        summary = send_lunch_reminders()

        self.assertEqual(summary['target_count'], 1)
        self.assertEqual(summary['failure_count'], 1)
        push_token.refresh_from_db()
        self.assertFalse(push_token.is_active)

    @patch('users.management.commands.send_lunch_push_reminders.send_lunch_reminders')
    def test_send_lunch_push_reminders_command(self, mocked_send_lunch_reminders):
        mocked_send_lunch_reminders.return_value = {
            'date': '2026-04-14',
            'target_count': 2,
            'success_count': 2,
            'failure_count': 0,
            'results': [],
        }

        call_command('send_lunch_push_reminders', '--date', '2026-04-14')

        mocked_send_lunch_reminders.assert_called_once()

    @patch('users.views.send_lunch_reminders')
    def test_admin_can_run_lunch_reminders(self, mocked_send_lunch_reminders):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        mocked_send_lunch_reminders.return_value = {
            'date': '2026-04-14',
            'target_count': 1,
            'success_count': 1,
            'failure_count': 0,
            'results': [],
        }

        response = self.client.post(
            '/admin/push/lunch-reminders/run/',
            {'date': '2026-04-14'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['target_count'], 1)
        mocked_send_lunch_reminders.assert_called_once()

    def test_get_my_inquiries_returns_only_current_user_items(self):
        Inquiry.objects.create(
            user=self.user,
            title='내 문의',
            content='내 내용',
            reply_email='user@example.com',
            status='PENDING',
        )
        other_user = User.objects.create_user(email='other@example.com', password='password123')
        Inquiry.objects.create(
            user=other_user,
            title='남의 문의',
            content='남의 내용',
            reply_email='other@example.com',
            status='RESOLVED',
        )

        response = self.client.get('/me/inquiries/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['title'], '내 문의')
        self.assertEqual(response.data['data'][0]['status'], 'PENDING')

    def test_announcements_returns_latest_one_when_none_selected(self):
        Announcement.objects.create(title='첫 공지', content='old')
        latest = Announcement.objects.create(title='최신 공지', content='new')

        response = self.client.get('/announcements')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], latest.id)
        self.assertFalse(response.data['data'][0]['is_selected_for_users'])

    def test_announcements_returns_selected_one_when_present(self):
        Announcement.objects.create(title='최신 공지', content='new')
        selected = Announcement.objects.create(
            title='선택 공지',
            content='selected',
            is_selected_for_users=True,
        )

        response = self.client.get('/announcements')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], selected.id)
        self.assertTrue(response.data['data'][0]['is_selected_for_users'])

    def test_patch_admin_announcement_selects_only_one(self):
        first = Announcement.objects.create(title='첫 공지', content='first', is_selected_for_users=True)
        second = Announcement.objects.create(title='둘째 공지', content='second')

        response = self.client.patch(
            f'/admin/announcements/{second.id}',
            {'is_selected_for_users': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_selected_for_users)
        self.assertTrue(second.is_selected_for_users)
