from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ProteinLog


User = get_user_model()


class ProteinApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            weight=70,
        )
        self.client.force_authenticate(self.user)

    def test_get_protein_overview(self):
        ProteinLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            amount=Decimal('25.0'),
            log_type=ProteinLog.LogType.QUICK,
        )

        response = self.client.get(reverse('protein_overview'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['consumed_amount'], '25.0')
        self.assertEqual(response.data['target_amount'], '112.0')
        self.assertEqual(len(response.data['logs']), 1)

    def test_create_protein_log(self):
        response = self.client.post(
            reverse('protein_log_create'),
            {'amount': '30.0', 'type': ProteinLog.LogType.MANUAL, 'note': 'chicken breast'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProteinLog.objects.count(), 1)

    def test_delete_protein_log(self):
        protein_log = ProteinLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            amount=Decimal('20.0'),
            log_type=ProteinLog.LogType.MEAL,
        )

        response = self.client.delete(reverse('protein_log_delete', args=[protein_log.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProteinLog.objects.filter(id=protein_log.id).exists())
