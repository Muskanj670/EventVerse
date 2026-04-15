from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile

from .models import Category, Event, Registration


class EventBookingTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username='organizer', password='pass12345')
        self.attendee = User.objects.create_user(username='attendee', password='pass12345')
        self.organizer.profile.role = UserProfile.Role.ORGANIZER
        self.organizer.profile.save()
        self.attendee.email = 'attendee@example.com'
        self.attendee.save(update_fields=['email'])
        self.attendee.profile.email_verified = True
        self.attendee.profile.phone = '+919876543210'
        self.attendee.profile.city = 'Delhi'
        self.attendee.profile.save()

        self.category, _ = Category.objects.get_or_create(name='Technology')
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.event = Event.objects.create(
            title='Future Tech Summit',
            description='A detailed event description for testing attendee bookings.',
            category=self.category,
            organizer=self.organizer,
            venue='Convention Center',
            city='Delhi',
            start_date=tomorrow,
            end_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(14, 0),
            capacity=10,
            price='499.00',
            status=Event.Status.PUBLISHED,
        )

    def test_booking_seats_creates_confirmed_registration(self):
        self.client.login(username='attendee', password='pass12345')

        response = self.client.post(
            reverse('events:event-book', args=[self.event.pk]),
            {'seat_count': 3},
            follow=True,
        )

        self.assertRedirects(response, reverse('events:event-detail', args=[self.event.pk]))
        registration = Registration.objects.get(user=self.attendee, event=self.event)
        self.assertEqual(registration.seat_count, 3)
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_seats, 7)

    def test_event_form_accepts_custom_category(self):
        self.client.login(username='organizer', password='pass12345')

        response = self.client.post(
            reverse('events:event-create'),
            {
                'title': 'Community Makers Meetup',
                'description': 'This community meetup explores local maker projects in depth.',
                'category': '',
                'custom_category': 'Community',
                'venue': 'Town Hall',
                'google_maps_url': 'https://maps.google.com/?q=Town+Hall',
                'city': 'Pune',
                'start_date': date.today() + timedelta(days=5),
                'end_date': date.today() + timedelta(days=5),
                'start_time': '11:00',
                'end_time': '13:00',
                'capacity': 25,
                'price': '0.00',
                'status': Event.Status.PUBLISHED,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        created_event = Event.objects.get(title='Community Makers Meetup')
        self.assertEqual(created_event.category.name, 'Community')

    def test_attendee_detail_view_hides_internal_registration_labels(self):
        self.client.login(username='attendee', password='pass12345')

        response = self.client.get(reverse('events:event-detail', args=[self.event.pk]))

        self.assertContains(response, 'Available Seats')
        self.assertNotContains(response, 'Registrations:')
        self.assertNotContains(response, 'Confirmed:')

    def test_booking_sends_confirmation_email(self):
        self.attendee.email = 'attendee@example.com'
        self.attendee.save(update_fields=['email'])
        self.client.login(username='attendee', password='pass12345')

        response = self.client.post(
            reverse('events:event-book', args=[self.event.pk]),
            {'seat_count': 2},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Booking confirmed for Future Tech Summit', mail.outbox[0].subject)

    def test_attendee_can_cancel_booking_and_email_notice_is_sent(self):
        self.attendee.email = 'attendee@example.com'
        self.attendee.save(update_fields=['email'])
        self.organizer.email = 'organizer@example.com'
        self.organizer.save(update_fields=['email'])
        self.client.login(username='attendee', password='pass12345')
        self.client.post(reverse('events:event-book', args=[self.event.pk]), {'seat_count': 2})

        response = self.client.post(reverse('events:event-cancel', args=[self.event.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        registration = Registration.objects.get(user=self.attendee, event=self.event)
        self.assertEqual(registration.status, Registration.Status.CANCELLED)
        self.assertIsNotNone(registration.cancelled_at)
        self.assertEqual(registration.cancelled_seat_count, 2)
        self.assertFalse(registration.reminder_enabled)
        self.assertEqual(len(mail.outbox), 3)
        self.assertIn('Booking cancelled for Future Tech Summit', mail.outbox[1].subject)
        self.assertIn('Attendee cancellation notice: Future Tech Summit', mail.outbox[2].subject)

    def test_attendee_can_partially_cancel_booking(self):
        self.attendee.email = 'attendee@example.com'
        self.attendee.save(update_fields=['email'])
        self.organizer.email = 'organizer@example.com'
        self.organizer.save(update_fields=['email'])
        self.client.login(username='attendee', password='pass12345')
        self.client.post(reverse('events:event-book', args=[self.event.pk]), {'seat_count': 4})

        response = self.client.post(reverse('events:event-cancel', args=[self.event.pk]), {'seat_count': 2}, follow=True)

        self.assertEqual(response.status_code, 200)
        registration = Registration.objects.get(user=self.attendee, event=self.event)
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertEqual(registration.seat_count, 2)
        self.assertEqual(registration.cancelled_seat_count, 2)
        self.assertTrue(registration.reminder_enabled)
        self.assertContains(response, 'Cancelled so far: 2 seats.')
        self.assertEqual(self.event.available_seats, 8)
        self.assertIn('Cancelled seats: 2', mail.outbox[1].body)

    def test_attendee_can_toggle_event_reminders(self):
        self.client.login(username='attendee', password='pass12345')
        self.client.post(reverse('events:event-book', args=[self.event.pk]), {'seat_count': 1})

        response = self.client.post(reverse('events:event-reminders', args=[self.event.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        registration = Registration.objects.get(user=self.attendee, event=self.event)
        self.assertFalse(registration.reminder_enabled)

    def test_send_event_reminders_command_sends_reminder_email(self):
        self.attendee.email = 'attendee@example.com'
        self.attendee.save(update_fields=['email'])
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.event.start_date = tomorrow
        self.event.end_date = tomorrow
        self.event.start_time = (timezone.localtime() + timedelta(hours=2)).time().replace(second=0, microsecond=0)
        self.event.end_time = (timezone.localtime() + timedelta(hours=4)).time().replace(second=0, microsecond=0)
        self.event.save(update_fields=['start_date', 'end_date', 'start_time', 'end_time'])
        self.client.login(username='attendee', password='pass12345')
        self.client.post(reverse('events:event-book', args=[self.event.pk]), {'seat_count': 1})

        call_command('send_event_reminders', '--hours', '36')

        registration = Registration.objects.get(user=self.attendee, event=self.event)
        self.assertIsNotNone(registration.reminder_sent_at)
        subjects = [email.subject for email in mail.outbox]
        self.assertIn('Reminder: Future Tech Summit starts soon', subjects)


class EventListFilterTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username='filter-organizer', password='pass12345')
        self.attendee = User.objects.create_user(username='filter-attendee', password='pass12345')
        self.category, _ = Category.objects.get_or_create(name='Music')

        today = timezone.localdate()
        self.upcoming_event = Event.objects.create(
            title='Beta Beats',
            description='Upcoming music showcase.',
            category=self.category,
            organizer=self.organizer,
            venue='Arena',
            city='Mumbai',
            start_date=today + timedelta(days=3),
            end_date=today + timedelta(days=3),
            start_time=time(18, 0),
            end_time=time(21, 0),
            capacity=50,
            price='300.00',
            status=Event.Status.PUBLISHED,
        )
        self.past_event = Event.objects.create(
            title='Alpha Acoustic',
            description='Past unplugged session.',
            category=self.category,
            organizer=self.organizer,
            venue='Studio',
            city='Mumbai',
            start_date=today - timedelta(days=5),
            end_date=today - timedelta(days=5),
            start_time=time(17, 0),
            end_time=time(19, 0),
            capacity=50,
            price='100.00',
            status=Event.Status.PUBLISHED,
        )
        self.expensive_event = Event.objects.create(
            title='Gamma Gala',
            description='Premium concert night.',
            category=self.category,
            organizer=self.organizer,
            venue='Hall',
            city='Mumbai',
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=10),
            start_time=time(20, 0),
            end_time=time(23, 0),
            capacity=50,
            price='900.00',
            status=Event.Status.PUBLISHED,
        )

        Registration.objects.create(
            user=self.attendee,
            event=self.upcoming_event,
            ticket=self.upcoming_event.tickets.first(),
            seat_count=4,
            status=Registration.Status.CONFIRMED,
        )
        Registration.objects.create(
            user=User.objects.create_user(username='second-attendee', password='pass12345'),
            event=self.expensive_event,
            ticket=self.expensive_event.tickets.first(),
            seat_count=7,
            status=Registration.Status.CONFIRMED,
        )

    def test_event_list_filters_by_upcoming_timing(self):
        response = self.client.get(reverse('events:event-list'), {'timing': 'upcoming'})

        events = list(response.context['events'])
        self.assertIn(self.upcoming_event, events)
        self.assertIn(self.expensive_event, events)
        self.assertNotIn(self.past_event, events)

    def test_event_list_sorts_by_highest_bookings(self):
        response = self.client.get(reverse('events:event-list'), {'sort': 'popular'})

        events = list(response.context['events'])
        self.assertEqual(events[0], self.expensive_event)
        self.assertEqual(events[1], self.upcoming_event)

    def test_event_list_sorts_alphabetically(self):
        response = self.client.get(reverse('events:event-list'), {'sort': 'title_asc'})

        events = list(response.context['events'])
        self.assertEqual(events[0], self.past_event)
        self.assertEqual(events[1], self.upcoming_event)
        self.assertEqual(events[2], self.expensive_event)

    def test_event_list_sorts_by_price(self):
        response = self.client.get(reverse('events:event-list'), {'sort': 'price_high'})

        events = list(response.context['events'])
        self.assertEqual(events[0], self.expensive_event)
        self.assertEqual(events[-1], self.past_event)

    def test_event_list_defaults_to_recent_upload_order(self):
        response = self.client.get(reverse('events:event-list'))

        events = list(response.context['events'])
        self.assertEqual(events[0], self.expensive_event)
        self.assertEqual(events[1], self.past_event)
        self.assertEqual(events[2], self.upcoming_event)
        self.assertEqual(response.context['selected_sort'], 'recent')

    def test_event_detail_navigation_respects_filtered_order(self):
        response = self.client.get(
            reverse('events:event-detail', args=[self.past_event.pk]),
            {'sort': 'recent'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['previous_event'], self.expensive_event)
        self.assertEqual(response.context['next_event'], self.upcoming_event)
        self.assertEqual(response.context['return_querystring'], '?sort=recent')
