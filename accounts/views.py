from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView

from .forms import CustomAuthenticationForm, SignupForm
from .models import VerificationOTP
from .utils import (
    create_signup_otp,
    get_user_role,
    get_valid_otp,
    mark_otp_verified,
    normalize_email,
    send_email_otp,
)
from events.models import Registration


class SignupView(CreateView):
    form_class = SignupForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your account has been created successfully. You can now log in.')
        return response


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, 'Welcome back. You are now logged in.')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('core:home')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class EmailValidationView(View):
    def get(self, request, *args, **kwargs):
        email = normalize_email(request.GET.get('email', ''))
        if not email:
            return JsonResponse({'valid': False, 'available': False, 'message': 'Email is required.'})

        exists = User.objects.filter(email__iexact=email).exists()
        if exists:
            return JsonResponse({'valid': True, 'available': False, 'message': 'This email is already in use.'})
        return JsonResponse({'valid': True, 'available': True, 'message': 'Email is available.'})


class UsernameValidationView(View):
    def get(self, request, *args, **kwargs):
        username = request.GET.get('username', '').strip()
        if not username:
            return JsonResponse({'valid': False, 'available': False, 'message': 'Username is required.'})
        if len(username) < 3:
            return JsonResponse(
                {'valid': False, 'available': False, 'message': 'Username must be at least 3 characters long.'}
            )

        exists = User.objects.filter(username__iexact=username).exists()
        if exists:
            return JsonResponse({'valid': True, 'available': False, 'message': 'This username is already taken.'})
        return JsonResponse({'valid': True, 'available': True, 'message': 'Username is available.'})


class SendEmailOTPView(View):
    def post(self, request, *args, **kwargs):
        email = normalize_email(request.POST.get('email', ''))
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'success': False, 'message': 'This email is already in use.'}, status=400)

        otp = create_signup_otp(email, VerificationOTP.Channel.EMAIL, VerificationOTP.Purpose.SIGNUP_EMAIL)
        send_email_otp(email, otp.code)
        return JsonResponse({'success': True, 'message': 'Email OTP sent successfully.'})


class VerifyEmailOTPView(View):
    def post(self, request, *args, **kwargs):
        email = normalize_email(request.POST.get('email', ''))
        code = request.POST.get('code', '').strip()
        otp = get_valid_otp(email, VerificationOTP.Channel.EMAIL, VerificationOTP.Purpose.SIGNUP_EMAIL, code)
        if not otp:
            return JsonResponse({'success': False, 'message': 'Invalid or expired email OTP.'}, status=400)
        mark_otp_verified(otp)
        return JsonResponse({'success': True, 'message': 'Email verified successfully.'})


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = get_user_role(self.request.user)
        can_view_booking_history = role == 'attendee'
        registrations = Registration.objects.none()
        managed_events = []

        if can_view_booking_history:
            registrations = (
                self.request.user.registrations.select_related('event', 'event__category')
                .order_by('-registered_at')
            )
        else:
            event_queryset = self.request.user.organized_events.select_related('category').order_by('start_date', 'start_time')
            if role == 'admin':
                event_queryset = event_queryset.model.objects.select_related('category', 'organizer').order_by(
                    'start_date', 'start_time'
                )

            now = timezone.now()
            managed_events = list(event_queryset[:3])
            managed_registrations = Registration.objects.filter(event__in=event_queryset)
            confirmed_registrations = managed_registrations.filter(status=Registration.Status.CONFIRMED)
            estimated_revenue = sum(
                (registration.event.price * registration.seat_count for registration in confirmed_registrations),
                0,
            )
            context['managed_events_count'] = event_queryset.count()
            context['upcoming_managed_events'] = sum(1 for event in event_queryset if event.end_datetime >= now)
            context['past_managed_events'] = sum(1 for event in event_queryset if event.end_datetime < now)
            context['managed_confirmed_seats'] = (
                confirmed_registrations.aggregate(total=Sum('seat_count'))['total'] or 0
            )
            context['managed_estimated_revenue'] = estimated_revenue

        context['profile'] = self.request.user.profile
        context['profile_role'] = role
        context['can_view_booking_history'] = can_view_booking_history
        context['booking_history'] = registrations
        context['managed_events_preview'] = managed_events
        context['total_booked_seats'] = sum(
            registration.seat_count
            for registration in registrations
            if registration.status == Registration.Status.CONFIRMED
        )
        context['total_cancelled_seats'] = sum(registration.cancelled_seat_count for registration in registrations)
        return context
