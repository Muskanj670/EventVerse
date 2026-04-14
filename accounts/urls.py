from django.urls import path

from .views import (
    CustomLoginView,
    CustomLogoutView,
    EmailValidationView,
    ProfileView,
    SendEmailOTPView,
    SignupView,
    UsernameValidationView,
    VerifyEmailOTPView,
)

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('send-email-otp/', SendEmailOTPView.as_view(), name='send-email-otp'),
    path('verify-email-otp/', VerifyEmailOTPView.as_view(), name='verify-email-otp'),
    path('validate-email/', EmailValidationView.as_view(), name='validate-email'),
    path('validate-username/', UsernameValidationView.as_view(), name='validate-username'),
]
