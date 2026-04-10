from django.urls import path

from .views import CustomLoginView, CustomLogoutView, EmailValidationView, SignupView

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('validate-email/', EmailValidationView.as_view(), name='validate-email'),
]
