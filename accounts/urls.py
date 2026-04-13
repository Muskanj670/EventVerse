from django.urls import path

from .views import CustomLoginView, CustomLogoutView, EmailValidationView, ProfileView, SignupView

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('validate-email/', EmailValidationView.as_view(), name='validate-email'),
]
