from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import CustomAuthenticationForm, ProfileUpdateForm, SignupForm
from .models import VerificationOTP
from .utils import (
    create_signup_otp,
    get_user_role,
    get_valid_otp,
    is_profile_ready_for_booking,
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
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect_url': str(self.success_url)})
        messages.success(self.request, 'Your account has been created successfully. You can now log in.')
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = list(field_errors)
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return super().form_invalid(form)


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
        raw_email = request.GET.get('email', '')
        email = normalize_email(raw_email)
        if not email:
            return JsonResponse({'valid': False, 'available': False, 'message': 'Email is required.'})

        try:
            SignupForm.validate_email_value(raw_email)
        except ValidationError as exc:
            return JsonResponse({'valid': False, 'available': False, 'message': exc.messages[0]})

        return JsonResponse({'valid': True, 'available': True, 'message': 'Email is available.'})


class UsernameValidationView(View):
    def get(self, request, *args, **kwargs):
        username = request.GET.get('username', '').strip()
        if not username:
            return JsonResponse({'valid': False, 'available': False, 'message': 'Username is required.'})

        try:
            SignupForm.validate_username_value(username)
        except ValidationError as exc:
            return JsonResponse({'valid': False, 'available': False, 'message': exc.messages[0]})

        return JsonResponse({'valid': True, 'available': True, 'message': 'Username is available.'})


class PasswordValidationView(View):
    def get(self, request, *args, **kwargs):
        password = request.GET.get('password', '')
        username = request.GET.get('username', '')
        email = request.GET.get('email', '')

        if not password:
            return JsonResponse({'valid': False, 'message': 'Password is required.'})

        try:
            SignupForm.validate_password_value(password, username=username, email=email)
        except ValidationError as exc:
            return JsonResponse({'valid': False, 'message': ' '.join(exc.messages)})

        return JsonResponse({'valid': True, 'message': 'Password looks good.'})


class SendEmailOTPView(View):
    def post(self, request, *args, **kwargs):
        raw_email = request.POST.get('email', '')
        email = normalize_email(raw_email)
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)

        try:
            email = SignupForm.validate_email_value(raw_email)
        except ValidationError as exc:
            return JsonResponse({'success': False, 'message': exc.messages[0]}, status=400)

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


class ProfileSendEmailOTPView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        raw_email = request.POST.get('email', '')
        email = normalize_email(raw_email)
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)

        try:
            email = SignupForm.base_fields['email'].clean(email)
        except ValidationError as exc:
            return JsonResponse({'success': False, 'message': exc.messages[0]}, status=400)

        if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            return JsonResponse({'success': False, 'message': 'This email is already in use.'}, status=400)

        otp = create_signup_otp(email, VerificationOTP.Channel.EMAIL, VerificationOTP.Purpose.PROFILE_EMAIL)
        send_email_otp(email, otp.code)
        return JsonResponse({'success': True, 'message': 'Verification OTP sent to your email.'})


class ProfileVerifyEmailOTPView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        email = normalize_email(request.POST.get('email', ''))
        code = request.POST.get('code', '').strip()
        otp = get_valid_otp(email, VerificationOTP.Channel.EMAIL, VerificationOTP.Purpose.PROFILE_EMAIL, code)
        if not otp:
            return JsonResponse({'success': False, 'message': 'Invalid or expired email OTP.'}, status=400)

        mark_otp_verified(otp)
        request.user.email = email
        request.user.save(update_fields=['email'])
        profile = request.user.profile
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
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
            upcoming_event_queryset = event_queryset.filter(
                Q(end_date__gt=now.date()) | Q(end_date=now.date(), end_time__gte=now.time())
            )
            managed_events = list(upcoming_event_queryset[:3])
            managed_registrations = Registration.objects.filter(event__in=event_queryset)
            confirmed_registrations = managed_registrations.filter(status=Registration.Status.CONFIRMED)
            estimated_revenue = sum(
                (registration.event.price * registration.seat_count for registration in confirmed_registrations),
                0,
            )
            context['managed_events_count'] = event_queryset.count()
            context['upcoming_managed_events'] = upcoming_event_queryset.count()
            context['past_managed_events'] = sum(1 for event in event_queryset if event.end_datetime < now)
            context['managed_confirmed_seats'] = (
                confirmed_registrations.aggregate(total=Sum('seat_count'))['total'] or 0
            )
            context['managed_estimated_revenue'] = estimated_revenue

        context['profile'] = self.request.user.profile
        context['profile_role'] = role
        context['profile_role_label'] = 'Admin' if role == 'admin' else self.request.user.profile.get_role_display()
        context['can_view_booking_history'] = can_view_booking_history
        context['booking_history'] = registrations
        context['managed_events_preview'] = managed_events
        context['can_book_events'] = is_profile_ready_for_booking(self.request.user)
        context['total_booked_seats'] = sum(
            registration.seat_count
            for registration in registrations
            if registration.status == Registration.Status.CONFIRMED
        )
        context['total_cancelled_seats'] = sum(registration.cancelled_seat_count for registration in registrations)
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'accounts/profile_edit.html'
    form_class = ProfileUpdateForm
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        previous_email = normalize_email(self.request.user.email or '')
        profile = form.save()
        if normalize_email(self.request.user.email or '') != previous_email:
            messages.info(self.request, 'Profile updated. Please verify your new email before booking events.')
        else:
            messages.success(self.request, 'Profile updated successfully.')
        if profile.email_verified and not self.request.user.email:
            messages.info(self.request, 'Add an email address to enable bookings.')
        return redirect(self.get_success_url())
