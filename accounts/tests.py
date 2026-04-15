from datetime import time, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import VerificationOTP
from events.models import Category, Event, Registration
from core.views import HomeView


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

    def test_organizer_profile_hides_booking_history(self):
        organizer = User.objects.create_user(username='organizer', password='pass12345')
        organizer.profile.role = 'organizer'
        organizer.profile.save()

        self.client.login(username='organizer', password='pass12345')
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Booking History')
        self.assertContains(response, 'Organizer Workspace')
        self.assertContains(response, 'Open Dashboard')
        self.assertContains(response, 'Quick Actions')

    def test_admin_profile_hides_booking_history(self):
        admin = User.objects.create_user(username='adminuser', password='pass12345', is_staff=True)

        self.client.login(username='adminuser', password='pass12345')
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Booking History')
        self.assertContains(response, 'Admin Control Hub')
        self.assertContains(response, 'Export registrations CSV')
        self.assertContains(response, 'Role:')
        self.assertContains(response, 'Admin')

    def test_organizer_profile_shows_management_stats(self):
        organizer = User.objects.create_user(username='host', password='pass12345')
        organizer.profile.role = 'organizer'
        organizer.profile.save()
        attendee = User.objects.create_user(username='guest', password='pass12345')
        category, _ = Category.objects.get_or_create(name='Tech')
        event_date = timezone.localdate() + timedelta(days=4)
        event = Event.objects.create(
            title='Creator Meetup',
            description='Meet local creators.',
            category=category,
            organizer=organizer,
            venue='Studio Hall',
            city='Pune',
            start_date=event_date,
            end_date=event_date,
            start_time=time(11, 0),
            end_time=time(13, 0),
            capacity=20,
            price='250.00',
            status=Event.Status.PUBLISHED,
        )
        Registration.objects.create(
            user=attendee,
            event=event,
            ticket=event.tickets.first(),
            seat_count=3,
            status=Registration.Status.CONFIRMED,
        )

        self.client.login(username='host', password='pass12345')
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Managed Events')
        self.assertContains(response, 'Creator Meetup')
        self.assertContains(response, 'Rs. 750.00')

    def test_organizer_profile_preview_shows_upcoming_events_only(self):
        organizer = User.objects.create_user(username='planner', password='pass12345')
        organizer.profile.role = 'organizer'
        organizer.profile.save()
        category, _ = Category.objects.get_or_create(name='Culture')
        today = timezone.localdate()
        past_event = Event.objects.create(
            title='Past Meetup',
            description='Already over.',
            category=category,
            organizer=organizer,
            venue='Old Hall',
            city='Delhi',
            start_date=today - timedelta(days=3),
            end_date=today - timedelta(days=3),
            start_time=time(10, 0),
            end_time=time(12, 0),
            capacity=20,
            price='100.00',
            status=Event.Status.PUBLISHED,
        )
        next_event = Event.objects.create(
            title='Next Meetup',
            description='Happening soon.',
            category=category,
            organizer=organizer,
            venue='New Hall',
            city='Delhi',
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            capacity=20,
            price='150.00',
            status=Event.Status.PUBLISHED,
        )
        later_event = Event.objects.create(
            title='Later Meetup',
            description='Happening later.',
            category=category,
            organizer=organizer,
            venue='Center',
            city='Delhi',
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=5),
            start_time=time(9, 0),
            end_time=time(11, 0),
            capacity=20,
            price='200.00',
            status=Event.Status.PUBLISHED,
        )

        self.client.login(username='planner', password='pass12345')
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        preview_events = response.context['managed_events_preview']
        self.assertEqual(preview_events[0], next_event)
        self.assertEqual(preview_events[1], later_event)
        self.assertNotIn(past_event, preview_events)


class HomeViewTests(TestCase):
    def test_home_featured_events_show_latest_uploaded_first(self):
        organizer = User.objects.create_user(username='home-organizer', password='pass12345')
        organizer.profile.role = 'organizer'
        organizer.profile.save()
        category, _ = Category.objects.get_or_create(name='Learning')
        today = timezone.localdate() + timedelta(days=7)

        first_event = Event.objects.create(
            title='First Upload',
            description='First event.',
            category=category,
            organizer=organizer,
            venue='Venue 1',
            city='Pune',
            start_date=today,
            end_date=today,
            start_time=time(10, 0),
            end_time=time(12, 0),
            capacity=25,
            price='100.00',
            status=Event.Status.PUBLISHED,
        )
        second_event = Event.objects.create(
            title='Second Upload',
            description='Second event.',
            category=category,
            organizer=organizer,
            venue='Venue 2',
            city='Pune',
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(12, 0),
            capacity=25,
            price='150.00',
            status=Event.Status.PUBLISHED,
        )

        request = self.client.get(reverse('core:home')).wsgi_request
        view = HomeView()
        view.setup(request)
        context = view.get_context_data()
        featured_events = list(context['featured_events'])

        self.assertEqual(featured_events[0], second_event)
        self.assertEqual(featured_events[1], first_event)

    def test_signup_requires_verified_email_and_phone_otps(self):
        response = self.client.post(
            reverse('accounts:signup'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'role': 'attendee',
                'phone': '9876543210',
                'city': 'Jaipur',
                'password1': 'StrongPass123',
                'password2': 'StrongPass123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify your email with OTP before signing up.')

    def test_signup_succeeds_after_verified_email_otp(self):
        self.client.post(reverse('accounts:send-email-otp'), {'email': 'newuser@example.com'})
        email_otp = VerificationOTP.objects.get(
            target='newuser@example.com',
            purpose=VerificationOTP.Purpose.SIGNUP_EMAIL,
        )
        self.client.post(
            reverse('accounts:verify-email-otp'),
            {'email': 'newuser@example.com', 'code': email_otp.code},
        )

        response = self.client.post(
            reverse('accounts:signup'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'role': 'attendee',
                'phone': '9876543210',
                'city': 'Jaipur',
                'password1': 'StrongPass123',
                'password2': 'StrongPass123',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        created_user = User.objects.get(username='newuser')
        self.assertTrue(created_user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Your EventVerse email OTP', mail.outbox[0].subject)

    def test_send_email_otp_does_not_expose_code_in_response(self):
        response = self.client.post(reverse('accounts:send-email-otp'), {'email': 'hiddenotp@example.com'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn('debug_otp', payload)
        self.assertNotIn('Dev OTP', payload['message'])

    def test_validate_username_reports_availability_in_realtime(self):
        User.objects.create_user(username='existinguser', password='pass12345')

        taken_response = self.client.get(reverse('accounts:validate-username'), {'username': 'existinguser'})
        available_response = self.client.get(reverse('accounts:validate-username'), {'username': 'freshuser'})

        self.assertEqual(taken_response.status_code, 200)
        self.assertFalse(taken_response.json()['available'])
        self.assertEqual(available_response.status_code, 200)
        self.assertTrue(available_response.json()['available'])

    def test_profile_edit_updates_details_and_marks_changed_email_unverified(self):
        user = User.objects.create_user(username='editor', password='pass12345', email='old@example.com')
        user.profile.email_verified = True
        user.profile.phone = '+919876543210'
        user.profile.city = 'Agra'
        user.profile.save()

        self.client.login(username='editor', password='pass12345')
        response = self.client.post(
            reverse('accounts:profile-edit'),
            {'email': 'new@example.com', 'phone': '9876543211', 'city': 'Delhi'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, 'new@example.com')
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(user.profile.city, 'Delhi')

    def test_profile_email_verification_marks_profile_verified(self):
        user = User.objects.create_user(username='verifyme', password='pass12345', email='verify@example.com')
        self.client.login(username='verifyme', password='pass12345')

        send_response = self.client.post(reverse('accounts:profile-send-email-otp'), {'email': 'verify@example.com'})
        self.assertEqual(send_response.status_code, 200)
        otp = VerificationOTP.objects.get(
            target='verify@example.com',
            purpose=VerificationOTP.Purpose.PROFILE_EMAIL,
        )

        verify_response = self.client.post(
            reverse('accounts:profile-verify-email-otp'),
            {'email': 'verify@example.com', 'code': otp.code},
        )

        self.assertEqual(verify_response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
