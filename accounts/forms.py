from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator

from .models import UserProfile, VerificationOTP
from .utils import (
    consume_verified_signup_otps,
    has_verified_signup_otp,
    normalize_email,
)


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.Role.choices)
    city = forms.CharField(max_length=120)

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'city', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    @classmethod
    def validate_username_value(cls, username):
        cleaned_username = (username or '').strip()
        username_field = User._meta.get_field('username')

        if len(cleaned_username) > username_field.max_length:
            raise forms.ValidationError(
                f'Ensure this value has at most {username_field.max_length} characters (it has {len(cleaned_username)}).'
            )

        UnicodeUsernameValidator()(cleaned_username)
        if User.objects.filter(username__iexact=cleaned_username).exists():
            raise forms.ValidationError('An account with this username already exists.')
        return cleaned_username

    @classmethod
    def validate_email_value(cls, email, *, require_verified_otp=False):
        cleaned_email = cls.base_fields['email'].clean(normalize_email(email))
        if User.objects.filter(email__iexact=cleaned_email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        if require_verified_otp and not has_verified_signup_otp(
            cleaned_email,
            VerificationOTP.Channel.EMAIL,
            VerificationOTP.Purpose.SIGNUP_EMAIL,
        ):
            raise forms.ValidationError('Verify your email with OTP before signing up.')
        return cleaned_email

    @classmethod
    def validate_password_value(cls, password, *, username='', email=''):
        user = User(username=(username or '').strip(), email=normalize_email(email or ''))
        password_validation.validate_password(password, user=user)
        return password

    def clean_email(self):
        return self.validate_email_value(self.cleaned_data['email'], require_verified_otp=True)

    def clean_username(self):
        return self.validate_username_value(self.cleaned_data['username'])

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        username = cleaned_data.get('username')
        if password1 and username and password1.lower() == username.lower():
            raise forms.ValidationError('Password cannot be the same as your username.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile = user.profile
        profile.role = self.cleaned_data['role']
        profile.city = self.cleaned_data['city']
        profile.email_verified = True
        if commit:
            profile.save(update_fields=['role', 'city', 'email_verified'])
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
        fields = ('city',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = self.user.email
        self.fields['city'].required = True
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = normalize_email(self.cleaned_data['email'])
        existing_user = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).first()
        if existing_user:
            raise forms.ValidationError('An account with this email already exists.')
        return email

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
