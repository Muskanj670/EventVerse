from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.utils import get_user_role, is_organizer_or_admin

from .forms import EventForm
from .models import Category, Event


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 6

    def get_queryset(self):
        queryset = Event.objects.select_related('organizer', 'category')
        category = self.request.GET.get('category')
        query = self.request.GET.get('q')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')

        if not is_organizer_or_admin(self.request.user):
            queryset = queryset.filter(status=Event.Status.PUBLISHED)

        if category:
            queryset = queryset.filter(category_id=category)
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if city:
            queryset = queryset.filter(city__icontains=city)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_city'] = self.request.GET.get('city', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['event_statuses'] = Event.Status.choices
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        context['tickets'] = event.tickets.all()
        context['registration_count'] = event.registrations.count()
        context['confirmed_registration_count'] = event.registrations.filter(status='confirmed').count()
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
