from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MealLog, ProteinLog, SchoolMealSelectionLog


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


class MealApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='meal@example.com',
            password='password123',
            weight=70,
        )
        self.client.force_authenticate(self.user)

    def test_get_meal_overview(self):
        MealLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type=MealLog.MealType.LUNCH,
            name='Chicken Salad',
            calories=450,
            protein=Decimal('35.0'),
            carbs=Decimal('20.0'),
            fat=Decimal('18.0'),
        )
        MealLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type=MealLog.MealType.SNACK,
            name='Greek Yogurt',
            calories=180,
            protein=Decimal('15.0'),
            carbs=Decimal('12.0'),
            fat=Decimal('5.0'),
        )

        response = self.client.get(reverse('meal_overview'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_calories'], 630)
        self.assertEqual(response.data['total_protein'], '50.0')
        self.assertEqual(len(response.data['meals']), 2)

    def test_create_meal_log(self):
        response = self.client.post(
            reverse('meal_log_create'),
            {
                'type': MealLog.MealType.DINNER,
                'name': 'Salmon Bowl',
                'calories': 520,
                'protein': '38.0',
                'carbs': '42.0',
                'fat': '20.0',
                'memo': 'extra vegetables',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MealLog.objects.count(), 1)
        self.assertEqual(MealLog.objects.first().name, 'Salmon Bowl')

    def test_delete_meal_log(self):
        meal_log = MealLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type=MealLog.MealType.BREAKFAST,
            name='Egg Toast',
            calories=320,
            protein=Decimal('18.0'),
            carbs=Decimal('28.0'),
            fat=Decimal('14.0'),
        )

        response = self.client.delete(reverse('meal_log_delete', args=[meal_log.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MealLog.objects.filter(id=meal_log.id).exists())

    def test_get_meal_overview_with_date_query_param(self):
        MealLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type=MealLog.MealType.LUNCH,
            name='Today Meal',
            calories=400,
            protein=Decimal('25.0'),
            carbs=Decimal('30.0'),
            fat=Decimal('10.0'),
        )
        MealLog.objects.create(
            user=self.user,
            date=timezone.datetime.strptime('2026-03-31', '%Y-%m-%d').date(),
            meal_type=MealLog.MealType.DINNER,
            name='Yesterday Meal',
            calories=700,
            protein=Decimal('45.0'),
            carbs=Decimal('60.0'),
            fat=Decimal('22.0'),
        )

        response = self.client.get(f"{reverse('meal_overview')}?date=2026-03-31")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['date'], '2026-03-31')
        self.assertEqual(response.data['total_calories'], 700)
        self.assertEqual(len(response.data['meals']), 1)

    @override_settings(
        NEIS_API_KEY='test-key',
        NEIS_ATPT_CODE='G10',
        NEIS_SCHOOL_CODE='7430310',
    )
    @patch('diet.views.fetch_school_lunch')
    def test_get_school_lunch(self, mock_fetch_school_lunch):
        mock_fetch_school_lunch.return_value = {
            'date': timezone.localdate(),
            'menus': [
                {'name': '닭갈비볶음', 'protein_grams': None},
                {'name': '계란국', 'protein_grams': None},
                {'name': '잡곡밥', 'protein_grams': None},
            ],
            'total_protein': 12.3,
            'calories': '850.5 Kcal',
            'nutrition_info': '탄수화물(g) 120.0<br/>단백질(g) 12.3<br/>지방(g) 20.1',
        }

        response = self.client.get(f"{reverse('school_lunch')}?meal_type=breakfast")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['school']['education_office_code'], 'G10')
        self.assertEqual(response.data['school']['school_code'], '7430310')
        self.assertEqual(response.data['meal_type'], 'breakfast')
        self.assertEqual(len(response.data['menus']), 2)
        self.assertEqual(response.data['estimated_total_protein'], 18.0)
        self.assertEqual(response.data['school_total_protein'], 12.3)
        self.assertEqual(response.data['menus'][0]['selection_options']['small'], 6.0)
        self.assertEqual(response.data['menus'][0]['selection_options']['medium'], 12.0)
        self.assertEqual(response.data['menus'][0]['selection_options']['large'], 18.0)

    def test_save_school_lunch_selection(self):
        response = self.client.post(
            reverse('school_lunch_log_save'),
            {
                'meal_type': 'breakfast',
                'items': [
                    {
                        'menu_name': '닭갈비볶음',
                        'selection': 'medium',
                        'estimated_protein_grams': '12.0',
                        'final_protein_grams': '12.0',
                    },
                    {
                        'menu_name': '계란국',
                        'selection': 'small',
                        'estimated_protein_grams': '6.0',
                        'final_protein_grams': '3.0',
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['meal_type'], 'breakfast')
        self.assertEqual(response.data['total_protein'], '15.0')
        self.assertEqual(SchoolMealSelectionLog.objects.count(), 2)

        protein_log = ProteinLog.objects.get(note='school-lunch:breakfast')
        self.assertEqual(protein_log.amount, Decimal('15.0'))

    def test_save_school_lunch_selection_overwrites_same_meal_type(self):
        SchoolMealSelectionLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type='breakfast',
            menu_name='이전메뉴',
            selection='medium',
            estimated_protein_grams='10.0',
            final_protein_grams='10.0',
        )
        ProteinLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            amount='10.0',
            log_type=ProteinLog.LogType.MEAL,
            note='school-lunch:breakfast',
        )

        response = self.client.post(
            reverse('school_lunch_log_save'),
            {
                'meal_type': 'breakfast',
                'items': [
                    {
                        'menu_name': '새메뉴',
                        'selection': 'large',
                        'estimated_protein_grams': '8.0',
                        'final_protein_grams': '12.0',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SchoolMealSelectionLog.objects.count(), 1)
        self.assertEqual(SchoolMealSelectionLog.objects.first().menu_name, '새메뉴')
        self.assertEqual(
            ProteinLog.objects.filter(note='school-lunch:breakfast').count(),
            1,
        )
        self.assertEqual(
            ProteinLog.objects.get(note='school-lunch:breakfast').amount,
            Decimal('12.0'),
        )
