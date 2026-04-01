from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class UserApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            onboarding_completed=True,
        )
        self.client.force_authenticate(self.user)

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
        self.user.refresh_from_db()
        self.assertEqual(self.user.height, 180)
        self.assertEqual(self.user.weight, 78)
        self.assertFalse(self.user.onboarding_completed)
