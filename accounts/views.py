from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView

from .forms import CustomAuthenticationForm, SignupForm


class SignupView(CreateView):
    form_class = SignupForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your account has been created successfully. Please log in.')
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
        email = request.GET.get('email', '').strip().lower()
        if not email:
            return JsonResponse({'valid': False, 'available': False, 'message': 'Email is required.'})

        exists = User.objects.filter(email__iexact=email).exists()
        if exists:
            return JsonResponse({'valid': True, 'available': False, 'message': 'This email is already in use.'})
        return JsonResponse({'valid': True, 'available': True, 'message': 'Email is available.'})
