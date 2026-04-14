from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile, VerificationOTP
from .utils import (
    consume_verified_signup_otps,
    has_verified_signup_otp,
    normalize_email,
    normalize_phone_number,
)


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.Role.choices)
    phone = forms.CharField(max_length=15)
    city = forms.CharField(max_length=120)

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'phone', 'city', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = normalize_email(self.cleaned_data['email'])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        if not has_verified_signup_otp(email, VerificationOTP.Channel.EMAIL, VerificationOTP.Purpose.SIGNUP_EMAIL):
            raise forms.ValidationError('Verify your email with OTP before signing up.')
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('An account with this username already exists.')
        return username

    def clean_phone(self):
        try:
            phone = normalize_phone_number(self.cleaned_data['phone'])
        except ValueError as exc:
            raise forms.ValidationError(str(exc))
        if UserProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError('An account with this phone number already exists.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.email = self.cleaned_data['email']
        if commit:
            user.save(update_fields=['email'])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data['role']
        profile.phone = self.cleaned_data['phone']
        profile.city = self.cleaned_data['city']
        profile.email_verified = True
        profile.phone_verified = False
        if commit:
            profile.save()
            consume_verified_signup_otps(self.cleaned_data['email'])
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing_class} form-control'.strip()


class OTPVerificationForm(forms.Form):
    target = forms.CharField(max_length=255)
    code = forms.CharField(max_length=6, min_length=6)
