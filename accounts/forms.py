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


class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ('phone', 'city')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = self.user.email
        self.fields['phone'].required = True
        self.fields['city'].required = True
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = normalize_email(self.cleaned_data['email'])
        existing_user = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).first()
        if existing_user:
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_phone(self):
        try:
            phone = normalize_phone_number(self.cleaned_data['phone'])
        except ValueError as exc:
            raise forms.ValidationError(str(exc))
        existing_profile = UserProfile.objects.filter(phone=phone).exclude(user=self.user).first()
        if existing_profile:
            raise forms.ValidationError('An account with this phone number already exists.')
        return phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        new_email = self.cleaned_data['email']
        email_changed = normalize_email(self.user.email or '') != new_email
        self.user.email = new_email
        if email_changed:
            profile.email_verified = False
        if commit:
            self.user.save(update_fields=['email'])
            profile.save()
        return profile


class OTPVerificationForm(forms.Form):
    target = forms.CharField(max_length=255)
    code = forms.CharField(max_length=6, min_length=6)
