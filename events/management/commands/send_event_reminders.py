from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.utils import send_event_reminder_email
from events.models import Registration


class Command(BaseCommand):
    help = 'Send reminder emails for upcoming confirmed event bookings.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Send reminders for events starting within this many hours (default: 24).',
        )

    def handle(self, *args, **options):
        hours = max(options['hours'], 1)
        now = timezone.now()
        window_end = now + timedelta(hours=hours)

        registrations = Registration.objects.select_related('user', 'event').filter(
            status=Registration.Status.CONFIRMED,
            reminder_enabled=True,
            reminder_sent_at__isnull=True,
            event__start_date__gte=now.date(),
            event__status='published',
        )

        total_candidates = 0
        reminders_sent = 0

        for registration in registrations:
            total_candidates += 1
            event_start = registration.event.start_datetime
            if event_start < now or event_start > window_end:
                continue

            email_sent = send_event_reminder_email(registration.user, registration.event, registration)
            if email_sent:
                registration.reminder_sent_at = now
                registration.save(update_fields=['reminder_sent_at'])
                reminders_sent += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {total_candidates} candidate registration(s); sent {reminders_sent} reminder email(s).'
            )
        )
