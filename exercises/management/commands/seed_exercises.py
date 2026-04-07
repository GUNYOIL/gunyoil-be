from django.core.management.base import BaseCommand
from django.db import transaction

from exercises.catalog import EXERCISE_CATALOG
from exercises.models import Exercise


class Command(BaseCommand):
    help = 'Sync exercise catalog from the code-defined source of truth.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prune',
            action='store_true',
            help='Mark exercises missing from the catalog as inactive.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        existing_by_code = {
            exercise.code: exercise
            for exercise in Exercise.objects.exclude(code__isnull=True).exclude(code='')
        }
        existing_by_name = {
            exercise.name: exercise
            for exercise in Exercise.objects.filter(code__isnull=True)
        }

        seen_codes = set()
        created_count = 0
        updated_count = 0
        reactivated_count = 0

        for item in EXERCISE_CATALOG:
            seen_codes.add(item['code'])

            exercise = existing_by_code.get(item['code'])
            if exercise is None:
                exercise = existing_by_name.get(item['name'])

            if exercise is None:
                Exercise.objects.create(**item, is_active=True)
                created_count += 1
                continue

            changed = False
            for field in ('code', 'name', 'category', 'target_muscle'):
                if getattr(exercise, field) != item[field]:
                    setattr(exercise, field, item[field])
                    changed = True

            if not exercise.is_active:
                exercise.is_active = True
                changed = True
                reactivated_count += 1

            if changed:
                exercise.save(update_fields=['code', 'name', 'category', 'target_muscle', 'is_active'])
                updated_count += 1

        deactivated_count = 0
        if options['prune']:
            deactivated_count = Exercise.objects.exclude(code__in=seen_codes).filter(is_active=True).update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f'Exercise sync complete: created={created_count}, updated={updated_count}, '
                f'reactivated={reactivated_count}, deactivated={deactivated_count}'
            )
        )
