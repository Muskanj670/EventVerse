from datetime import date, time, timedelta

from django.contrib.auth.models import User
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
