from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.utils import (
    get_user_role,
    is_profile_ready_for_booking,
    is_organizer_or_admin,
    send_booking_notifications,
    send_cancellation_notifications,
)

from .forms import BookingCancellationForm, BookingForm, EventForm
from .models import Category, Event, Registration


def get_event_list_queryset(request, include_registrations=False):
    queryset = Event.objects.select_related('organizer', 'category').prefetch_related('media_assets')
    if include_registrations:
        queryset = queryset.prefetch_related('registrations')
    queryset = queryset.annotate(
        confirmed_bookings=Coalesce(
            Sum(
                'registrations__seat_count',
                filter=Q(registrations__status=Registration.Status.CONFIRMED),
            ),
            Value(0),
            output_field=IntegerField(),
        )
    )

    category = request.GET.get('category')
    query = request.GET.get('q')
    city = request.GET.get('city')
    timing = request.GET.get('timing')
    sort = request.GET.get('sort', 'recent')
    now = timezone.localtime()

    if not is_organizer_or_admin(request.user):
        queryset = queryset.filter(status=Event.Status.PUBLISHED)

    if category:
        queryset = queryset.filter(category_id=category)
    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if city:
        queryset = queryset.filter(city__icontains=city)

    past_filter = Q(end_date__lt=now.date()) | Q(end_date=now.date(), end_time__lt=now.time())
    if timing == 'upcoming':
        queryset = queryset.exclude(past_filter)
    elif timing == 'past':
        queryset = queryset.filter(past_filter)

    sort_map = {
        'recent': ('-created_at', '-id'),
        'popular': ('-confirmed_bookings', 'start_date', 'start_time', 'title'),
        'title_asc': ('title',),
        'title_desc': ('-title',),
        'price_low': ('price', 'start_date', 'start_time', 'title'),
        'price_high': ('-price', 'start_date', 'start_time', 'title'),
        'schedule': ('start_date', 'start_time', '-created_at'),
    }
    return queryset.order_by(*sort_map.get(sort, sort_map['schedule']))


class EventListView(ListView):
    SORT_OPTIONS = (
        ('schedule', 'Event date'),
        ('recent', 'Recently uploaded'),
        ('popular', 'Highest bookings'),
        ('title_asc', 'Alphabetical (A-Z)'),
        ('title_desc', 'Alphabetical (Z-A)'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
    )

    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 6

    def get_queryset(self):
        return get_event_list_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_city'] = self.request.GET.get('city', '')
        context['selected_timing'] = self.request.GET.get('timing', '')
        context['selected_sort'] = self.request.GET.get('sort', 'recent')
        context['sort_options'] = self.SORT_OPTIONS
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return get_event_list_queryset(self.request, include_registrations=True).prefetch_related('tickets')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        querystring = self.request.GET.urlencode()
        event_ids = list(self.get_queryset().values_list('pk', flat=True))
        previous_event = None
        next_event = None
        if event.pk in event_ids:
            event_index = event_ids.index(event.pk)
            if event_index > 0:
                previous_event = Event.objects.get(pk=event_ids[event_index - 1])
            if event_index < len(event_ids) - 1:
                next_event = Event.objects.get(pk=event_ids[event_index + 1])

        context['tickets'] = event.tickets.all()
        context['booking_form'] = BookingForm(event=event)
        context['can_book'] = (
            self.request.user.is_authenticated
            and not is_organizer_or_admin(self.request.user)
            and event.status == Event.Status.PUBLISHED
            and event.end_datetime >= timezone.now()
            and event.available_seats > 0
            and is_profile_ready_for_booking(self.request.user)
        )
        context['profile_ready_for_booking'] = (
            is_profile_ready_for_booking(self.request.user) if self.request.user.is_authenticated else False
        )
        context['user_registration'] = (
            event.registrations.filter(user=self.request.user).first() if self.request.user.is_authenticated else None
        )
        context['cancellation_form'] = BookingCancellationForm(registration=context['user_registration'])
        context['can_cancel_booking'] = (
            context['user_registration']
            and context['user_registration'].status == Registration.Status.CONFIRMED
            and event.end_datetime >= timezone.now()
        )
        context['previous_event'] = previous_event
        context['next_event'] = next_event
        context['return_querystring'] = f'?{querystring}' if querystring else ''
        return context


class EventOwnerMixin(UserPassesTestMixin):
    def test_func(self):
        event = self.get_object()
        return event.created_by == self.request.user or get_user_role(self.request.user) == 'admin'

    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to modify this event.')
        return super().handle_no_permission()


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_organizer_or_admin(request.user):
            messages.error(request, 'Only organizers and admins can create events.')
            return redirect('events:event-list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        messages.success(self.request, 'Event created successfully.')
        return super().form_valid(form)


class EventUpdateView(LoginRequiredMixin, EventOwnerMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Event updated successfully.')
        return super().form_valid(form)


class EventDeleteView(LoginRequiredMixin, EventOwnerMixin, DeleteView):
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('dashboard:dashboard-home')

    def form_valid(self, form):
        messages.success(self.request, 'Event deleted successfully.')
        return super().form_valid(form)


def book_event_seats(request, pk):
    event = get_object_or_404(
        Event.objects.select_related('organizer', 'category').prefetch_related('tickets', 'media_assets'),
        pk=pk,
        status=Event.Status.PUBLISHED,
    )

    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to book seats for this event.')
        return redirect('accounts:login')

    if is_organizer_or_admin(request.user):
        messages.error(request, 'Organizer and admin accounts cannot book seats from the attendee view.')
        return redirect('events:event-detail', pk=event.pk)

    if request.method != 'POST':
        return redirect('events:event-detail', pk=event.pk)

    if not is_profile_ready_for_booking(request.user):
        messages.error(request, 'Complete your profile and verify your email before booking events.')
        return redirect('accounts:profile-edit')

    if event.end_datetime < timezone.now():
        messages.error(request, 'This event has already ended.')
        return redirect('events:event-detail', pk=event.pk)

    form = BookingForm(request.POST, event=event)
    if form.is_valid():
        registration = form.save(request.user)
        notification_status = send_booking_notifications(request.user, event, registration)
        confirmation_text = 'email' if notification_status['email_sent'] else 'onscreen message'
        messages.success(
            request,
            f'{registration.seat_count} seat(s) booked successfully for {event.title}. Confirmation sent via {confirmation_text}.',
        )
    else:
        for error in form.errors.get('seat_count', []):
            messages.error(request, error)

    return redirect('events:event-detail', pk=event.pk)


def cancel_event_booking(request, pk):
    event = get_object_or_404(Event.objects.select_related('organizer'), pk=pk)

    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to manage your booking.')
        return redirect('accounts:login')

    if request.method != 'POST':
        return redirect('events:event-detail', pk=event.pk)

    registration = event.registrations.filter(user=request.user).first()
    if not registration or registration.status != Registration.Status.CONFIRMED:
        messages.error(request, 'No active booking found to cancel.')
        return redirect('events:event-detail', pk=event.pk)

    cancellation_data = request.POST.copy()
    if not cancellation_data.get('seat_count'):
        cancellation_data['seat_count'] = str(registration.seat_count)

    form = BookingCancellationForm(cancellation_data, registration=registration)
    if not form.is_valid():
        for error in form.errors.get('seat_count', []):
            messages.error(request, error)
        return redirect('events:event-detail', pk=event.pk)

    cancelled_seats = form.cleaned_data['seat_count']
    registration.seat_count -= cancelled_seats
    registration.cancelled_seat_count += cancelled_seats
    registration.cancelled_at = timezone.now()
    registration.reminder_enabled = registration.seat_count > 0 and registration.reminder_enabled
    if registration.seat_count == 0:
        registration.status = Registration.Status.CANCELLED
        registration.reminder_enabled = False
    registration.save(update_fields=['seat_count', 'cancelled_seat_count', 'status', 'cancelled_at', 'reminder_enabled'])

    notification_status = send_cancellation_notifications(
        request.user,
        event,
        registration,
        cancelled_seats=cancelled_seats,
    )
    if notification_status['attendee_email_sent'] or notification_status['organizer_email_sent']:
        if registration.status == Registration.Status.CANCELLED:
            messages.success(request, 'Your booking has been cancelled and an email notice has been sent.')
        else:
            messages.success(request, f'{cancelled_seats} seat(s) have been cancelled and an email notice has been sent.')
    else:
        if registration.status == Registration.Status.CANCELLED:
            messages.success(request, 'Your booking has been cancelled successfully.')
        else:
            messages.success(request, f'{cancelled_seats} seat(s) have been cancelled successfully.')

    return redirect('events:event-detail', pk=event.pk)


def toggle_event_reminders(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to manage reminders.')
        return redirect('accounts:login')

    if request.method != 'POST':
        return redirect('events:event-detail', pk=event.pk)

    registration = event.registrations.filter(user=request.user, status=Registration.Status.CONFIRMED).first()
    if not registration:
        messages.error(request, 'You need a confirmed booking to manage reminders.')
        return redirect('events:event-detail', pk=event.pk)

    registration.reminder_enabled = not registration.reminder_enabled
    if registration.reminder_enabled:
        registration.reminder_sent_at = None
    registration.save(update_fields=['reminder_enabled', 'reminder_sent_at'])

    if registration.reminder_enabled:
        messages.success(request, 'Event reminders have been enabled for this booking.')
    else:
        messages.info(request, 'Event reminders have been disabled for this booking.')

    return redirect('events:event-detail', pk=event.pk)
