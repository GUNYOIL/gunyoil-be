from datetime import date

from django.core.management.base import BaseCommand, CommandError

from users.push_notifications import send_lunch_reminders


class Command(BaseCommand):
    help = 'Send lunch reminder push notifications to users who have not recorded lunch for the target date.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            dest='target_date',
            help='Target date in YYYY-MM-DD format. Defaults to today.',
        )

    def handle(self, *args, **options):
        target_date = None
        if options['target_date']:
            try:
                target_date = date.fromisoformat(options['target_date'])
            except ValueError as exc:
                raise CommandError('date must be in YYYY-MM-DD format.') from exc

        summary = send_lunch_reminders(target_date=target_date)

        self.stdout.write(
            self.style.SUCCESS(
                f"date={summary['date']} targets={summary['target_count']} "
                f"success={summary['success_count']} failure={summary['failure_count']}"
            )
        )
