import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import UserProfile, VerificationOTP


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        return 'admin'
    return UserProfile.objects.filter(user=user).values_list('role', flat=True).first() or UserProfile.Role.ATTENDEE


def is_organizer_or_admin(user):
    role = get_user_role(user)
    return role in {'organizer', 'admin'}


def normalize_email(email):
    return email.strip().lower()


def normalize_phone_number(phone):
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:
        return f'+91{digits}'
    if phone.strip().startswith('+') and 10 <= len(digits) <= 15:
        return f'+{digits}'
    if phone.strip().startswith('00') and 10 <= len(digits) <= 15:
        return f'+{digits[2:]}'
    raise ValueError('Enter a valid phone number in 10-digit or international format.')


def generate_otp_code():
    return ''.join(secrets.choice('0123456789') for _ in range(6))


def create_signup_otp(target, channel, purpose):
    VerificationOTP.objects.filter(target=target, channel=channel, purpose=purpose).delete()
    return VerificationOTP.objects.create(
        target=target,
        channel=channel,
        purpose=purpose,
        code=generate_otp_code(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def get_valid_otp(target, channel, purpose, code):
    return VerificationOTP.objects.filter(
        target=target,
        channel=channel,
        purpose=purpose,
        code=code,
        is_verified=False,
        expires_at__gte=timezone.now(),
    ).first()


def mark_otp_verified(otp):
    otp.is_verified = True
    otp.verified_at = timezone.now()
    otp.save(update_fields=['is_verified', 'verified_at'])


def has_verified_signup_otp(target, channel, purpose):
    return VerificationOTP.objects.filter(
        target=target,
        channel=channel,
        purpose=purpose,
        is_verified=True,
        expires_at__gte=timezone.now(),
    ).exists()


def consume_verified_signup_otps(email):
    VerificationOTP.objects.filter(
        target=email,
        purpose=VerificationOTP.Purpose.SIGNUP_EMAIL,
        is_verified=True,
    ).delete()


def is_profile_ready_for_booking(user):
    if not user.is_authenticated:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return bool(user.email and profile.email_verified and profile.phone and profile.city)


def send_email_otp(email, otp_code):
    send_mail(
        subject='Your EventVerse email OTP',
        message=f'Your EventVerse email verification OTP is {otp_code}. It expires in 10 minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def send_booking_notifications(user, event, registration):
    email_sent = False

    if user.email:
        send_mail(
            subject=f'Booking confirmed for {event.title}',
            message=(
                f'Hi {user.username},\n\n'
                f'Your booking for {event.title} is confirmed.\n'
                f'Seats booked: {registration.seat_count}\n'
                f'Date: {event.start_date}\n'
                f'Time: {event.start_time} - {event.end_time}\n'
                f'Venue: {event.venue}, {event.city}\n\n'
                'Thank you for booking with EventVerse.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        email_sent = True

    return {'email_sent': email_sent}


def send_cancellation_notifications(user, event, registration, cancelled_seats=None):
    attendee_email_sent = False
    organizer_email_sent = False
    cancelled_seats = cancelled_seats if cancelled_seats is not None else registration.seat_count

    if user.email:
        send_mail(
            subject=f'Booking cancelled for {event.title}',
            message=(
                f'Hi {user.username},\n\n'
                f'Your booking for {event.title} has been cancelled.\n'
                f'Cancelled seats: {cancelled_seats}\n'
                f'Date: {event.start_date}\n'
                f'Time: {event.start_time} - {event.end_time}\n'
                f'Venue: {event.venue}, {event.city}\n\n'
                'If this was a mistake, you can book again from the event page.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        attendee_email_sent = True

    organizer = event.organizer
    if organizer and organizer.email:
        send_mail(
            subject=f'Attendee cancellation notice: {event.title}',
            message=(
                f'Hello {organizer.username},\n\n'
                f'{user.username} has cancelled their booking for {event.title}.\n'
                f'Cancelled seats: {cancelled_seats}\n'
                f'Event date: {event.start_date}\n'
                f'Event time: {event.start_time} - {event.end_time}\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[organizer.email],
            fail_silently=True,
        )
        organizer_email_sent = True

    return {'attendee_email_sent': attendee_email_sent, 'organizer_email_sent': organizer_email_sent}


def send_event_reminder_email(user, event, registration):
    if not user.email:
        return False

    send_mail(
        subject=f'Reminder: {event.title} starts soon',
        message=(
            f'Hi {user.username},\n\n'
            f'This is a reminder for your upcoming event booking.\n'
            f'Event: {event.title}\n'
            f'Seats: {registration.seat_count}\n'
            f'Date: {event.start_date}\n'
            f'Time: {event.start_time} - {event.end_time}\n'
            f'Venue: {event.venue}, {event.city}\n\n'
            'See you there.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    return True
