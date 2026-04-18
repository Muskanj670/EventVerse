import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from events.models import Category, Event, Registration


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username='organizer', password='pass12345')
        self.organizer.profile.role = UserProfile.Role.ORGANIZER
        self.organizer.profile.save()
        self.attendee = User.objects.create_user(username='attendee', password='pass12345')
        self.category, _ = Category.objects.get_or_create(name='Technology')

    def test_past_events_include_events_that_already_ended_today(self):
        today = timezone.localdate()
        now = timezone.localtime()
        past_end_time = (now - timedelta(hours=2)).time().replace(second=0, microsecond=0)
        past_start_time = (now - timedelta(hours=4)).time().replace(second=0, microsecond=0)
        upcoming_start_time = (now + timedelta(hours=2)).time().replace(second=0, microsecond=0)
        upcoming_end_time = (now + timedelta(hours=4)).time().replace(second=0, microsecond=0)

        past_event = Event.objects.create(
            title='Morning Session',
            description='A completed event that ended earlier today.',
            category=self.category,
            organizer=self.organizer,
            venue='Hall A',
            city='Delhi',
            start_date=today,
            end_date=today,
            start_time=past_start_time,
            end_time=past_end_time,
            capacity=10,
            price='250.00',
            status=Event.Status.PUBLISHED,
        )
        upcoming_event = Event.objects.create(
            title='Evening Session',
            description='An upcoming event scheduled for later today.',
            category=self.category,
            organizer=self.organizer,
            venue='Hall B',
            city='Delhi',
            start_date=today,
            end_date=today,
            start_time=upcoming_start_time,
            end_time=upcoming_end_time,
            capacity=10,
            price='400.00',
            status=Event.Status.PUBLISHED,
        )
        Registration.objects.create(
            user=self.attendee,
            event=past_event,
            ticket=past_event.tickets.first(),
            seat_count=2,
            status=Registration.Status.CONFIRMED,
        )

        self.client.login(username='organizer', password='pass12345')
        response = self.client.get(reverse('dashboard:dashboard-home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['past_events'], 1)
        self.assertEqual(response.context['upcoming_events'], 1)
        self.assertEqual(response.context['confirmed_registrations'], 2)
        self.assertEqual(response.context['estimated_revenue'], Decimal('500.00'))

    def test_dashboard_exposes_registration_and_occupancy_chart_data(self):
        today = timezone.localdate()
        now = timezone.localtime()
        start_time = (now + timedelta(hours=1)).time().replace(second=0, microsecond=0)
        end_time = (now + timedelta(hours=3)).time().replace(second=0, microsecond=0)

        first_event = Event.objects.create(
            title='AI Summit',
            description='A published event with stronger registration volume.',
            category=self.category,
            organizer=self.organizer,
            venue='Hall A',
            city='Delhi',
            start_date=today,
            end_date=today,
            start_time=start_time,
            end_time=end_time,
            capacity=10,
            price='100.00',
            status=Event.Status.PUBLISHED,
        )
        second_event = Event.objects.create(
            title='Cloud Expo',
            description='A second event with lighter registration volume.',
            category=self.category,
            organizer=self.organizer,
            venue='Hall B',
            city='Delhi',
            start_date=today,
            end_date=today,
            start_time=start_time,
            end_time=end_time,
            capacity=20,
            price='150.00',
            status=Event.Status.PUBLISHED,
        )

        first_registration = Registration.objects.create(
            user=self.attendee,
            event=first_event,
            ticket=first_event.tickets.first(),
            seat_count=4,
            status=Registration.Status.CONFIRMED,
        )
        second_attendee = User.objects.create_user(username='attendee_two', password='pass12345')
        second_registration = Registration.objects.create(
            user=second_attendee,
            event=second_event,
            ticket=second_event.tickets.first(),
            seat_count=5,
            status=Registration.Status.CONFIRMED,
        )

        registration_month = timezone.localtime(first_registration.registered_at).strftime('%b %Y')
        Registration.objects.filter(pk__in=[first_registration.pk, second_registration.pk]).update(
            registered_at=timezone.now() - timedelta(days=2)
        )

        self.client.login(username='organizer', password='pass12345')
        response = self.client.get(reverse('dashboard:dashboard-home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.context['chart_event_labels']), ['Cloud Expo', 'AI Summit'])
        self.assertEqual(json.loads(response.context['chart_event_totals']), [5, 4])
        self.assertEqual(json.loads(response.context['chart_month_labels']), [registration_month])
        self.assertEqual(json.loads(response.context['chart_month_totals']), [9])
        self.assertEqual(response.context['seat_occupancy_percentage'], 30.0)
