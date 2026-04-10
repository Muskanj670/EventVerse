from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Category, Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title',
            'description',
            'category',
            'venue',
            'city',
            'start_date',
            'end_date',
            'start_time',
            'end_time',
            'capacity',
            'price',
            'status',
            'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter event title'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe your event'}),
            'category': forms.Select(),
            'venue': forms.TextInput(attrs={'placeholder': 'Enter venue name'}),
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
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

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

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        capacity = cleaned_data.get('capacity')
        price = cleaned_data.get('price')

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

        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image size must be 5 MB or less.')
        return image
