from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Category, Event, EventMedia, Registration


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data if item]
        if not data:
            return []
        return [single_file_clean(data, initial)]


class EventForm(forms.ModelForm):
    custom_category = forms.CharField(
        required=False,
        max_length=100,
        help_text='Use this if the event category is not listed above.',
    )
    media_files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'accept': 'image/*,video/*'}),
        help_text='Upload multiple images or videos for the event carousel.',
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'description',
            'category',
            'custom_category',
            'venue',
            'google_maps_url',
            'city',
            'start_date',
            'end_date',
            'start_time',
            'end_time',
            'capacity',
            'price',
            'status',
            'media_files',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter event title'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe your event'}),
            'category': forms.Select(),
            'venue': forms.TextInput(attrs={'placeholder': 'Enter venue name'}),
            'google_maps_url': forms.URLInput(attrs={'placeholder': 'Paste Google Maps link'}),
            'city': forms.TextInput(attrs={'placeholder': 'Enter city'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'capacity': forms.NumberInput(attrs={'min': 1}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'status': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].required = False
        self.fields['category'].empty_label = 'Other / Custom Category'
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
        self._media_files = []

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 5:
            raise forms.ValidationError('Title must be at least 5 characters long.')
        return title

    def clean_description(self):
        description = self.cleaned_data['description'].strip()
        if len(description) < 20:
            raise forms.ValidationError('Description must be at least 20 characters long.')
        return description

    def clean_custom_category(self):
        return self.cleaned_data.get('custom_category', '').strip()

    def clean_media_files(self):
        media_files = self.files.getlist('media_files')
        allowed_image_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        allowed_video_types = {'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'}

        for media in media_files:
            content_type = getattr(media, 'content_type', '')
            if media.size > 25 * 1024 * 1024:
                raise forms.ValidationError('Each media file must be 25 MB or less.')
            if content_type not in allowed_image_types | allowed_video_types:
                raise forms.ValidationError('Only JPG, PNG, WEBP, GIF, MP4, WEBM, OGG, and MOV files are supported.')

        self._media_files = media_files
        return media_files

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        capacity = cleaned_data.get('capacity')
        price = cleaned_data.get('price')
        category = cleaned_data.get('category')
        custom_category = cleaned_data.get('custom_category')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be earlier than start date.')

        if start_date and end_date and start_time and end_time and start_date == end_date and end_time <= start_time:
            self.add_error('end_time', 'End time must be after start time for a same-day event.')

        if start_date and start_date < (timezone.localdate() - timedelta(days=3650)):
            self.add_error('start_date', 'Please enter a valid event start date.')

        if capacity is not None and capacity < 1:
            self.add_error('capacity', 'Capacity must be at least 1.')

        if price is not None and price < 0:
            self.add_error('price', 'Price cannot be negative.')

        if not category and not custom_category:
            self.add_error('category', 'Select a category or enter a custom category.')
        if custom_category and len(custom_category) < 3:
            self.add_error('custom_category', 'Custom category must be at least 3 characters long.')

        return cleaned_data

    def save(self, commit=True):
        custom_category = self.cleaned_data.get('custom_category')
        if custom_category:
            category, _ = Category.objects.get_or_create(name=custom_category)
            self.instance.category = category

        event = super().save(commit=commit)

        if commit:
            for media in self._media_files:
                content_type = getattr(media, 'content_type', '')
                media_type = (
                    EventMedia.MediaType.IMAGE if content_type.startswith('image/') else EventMedia.MediaType.VIDEO
                )
                EventMedia.objects.create(event=event, file=media, media_type=media_type)

        return event


class BookingForm(forms.Form):
    seat_count = forms.IntegerField(min_value=1, label='Seats')

    def __init__(self, *args, event=None, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)
        self.fields['seat_count'].widget.attrs['class'] = 'form-control'

    def clean_seat_count(self):
        seat_count = self.cleaned_data['seat_count']
        if self.event and seat_count > self.event.available_seats:
            raise forms.ValidationError('Requested seats exceed the number of available seats.')
        return seat_count

    def save(self, user):
        self.event.ensure_default_ticket()
        ticket = self.event.tickets.order_by('id').first()
        registration, created = Registration.objects.get_or_create(
            user=user,
            event=self.event,
            ticket=ticket,
            defaults={
                'seat_count': self.cleaned_data['seat_count'],
                'status': Registration.Status.CONFIRMED,
            },
        )
        if not created:
            registration.seat_count += self.cleaned_data['seat_count']
            registration.status = Registration.Status.CONFIRMED
            registration.save(update_fields=['seat_count', 'status'])
        return registration
