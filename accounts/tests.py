from datetime import time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Category, Event, Registration


class ProfileViewTests(TestCase):
    def test_profile_page_lists_booking_history(self):
        user = User.objects.create_user(username='attendee', password='pass12345')
        organizer = User.objects.create_user(username='organizer', password='pass12345')
        organizer.profile.role = 'organizer'
        organizer.profile.save()
        category, _ = Category.objects.get_or_create(name='Business')
        event_date = timezone.localdate() + timedelta(days=2)
        event = Event.objects.create(
            title='Startup Circle',
            description='A business networking event focused on startup growth and partnerships.',
            category=category,
            organizer=organizer,
            venue='Innovation Hub',
            city='Bengaluru',
            start_date=event_date,
            end_date=event_date,
            start_time=time(15, 0),
            end_time=time(18, 0),
            capacity=30,
            price='999.00',
            status=Event.Status.PUBLISHED,
        )
        Registration.objects.create(
            user=user,
            event=event,
            ticket=event.tickets.first(),
            seat_count=2,
            status=Registration.Status.CONFIRMED,
        )

        self.client.login(username='attendee', password='pass12345')
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Booking History')
        self.assertContains(response, 'Startup Circle')
        self.assertContains(response, '2')
