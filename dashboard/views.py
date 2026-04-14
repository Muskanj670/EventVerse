import json
import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.utils import get_user_role, is_organizer_or_admin
from events.models import Event, Registration


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_organizer_or_admin(request.user):
            messages.info(request, 'Dashboard analytics are available for organizer and admin accounts.')
            return redirect('events:event-list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Event.objects.select_related('organizer', 'category').prefetch_related('media_assets')
        if get_user_role(self.request.user) != 'admin':
            queryset = queryset.filter(organizer=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        now = timezone.now()

        paginator = Paginator(queryset, 6)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        events = list(queryset)

        category_stats = list(
            queryset.values('category__name')
            .annotate(total=Count('id'))
            .order_by('category__name')
        )
        monthly_stats = list(
            queryset.annotate(month=TruncMonth('start_date'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )
        registrations = Registration.objects.filter(event__in=queryset)
        if get_user_role(self.request.user) != 'admin':
            registrations = registrations.filter(event__organizer=self.request.user)
        confirmed_registrations_qs = registrations.filter(status=Registration.Status.CONFIRMED)
        total_revenue = sum(
            (registration.event.price * registration.seat_count for registration in confirmed_registrations_qs),
            Decimal('0.00'),
        )
        upcoming_events = sum(1 for event in events if event.end_datetime >= now)
        past_events = sum(1 for event in events if event.end_datetime < now)
        confirmed_registrations = confirmed_registrations_qs.aggregate(total=Sum('seat_count'))['total'] or 0

        context.update(
            {
                'events': page_obj.object_list,
                'page_obj': page_obj,
                'paginator': paginator,
                'is_paginated': page_obj.has_other_pages(),
                'total_events': queryset.count(),
                'upcoming_events': upcoming_events,
                'past_events': past_events,
                'this_month_events': queryset.filter(start_date__year=now.year, start_date__month=now.month).count(),
                'confirmed_registrations': confirmed_registrations,
                'estimated_revenue': total_revenue,
                'chart_category_labels': json.dumps(
                    [item['category__name'] for item in category_stats]
                ),
                'chart_category_totals': json.dumps([item['total'] for item in category_stats]),
                'chart_status_totals': json.dumps(
                    [
                        upcoming_events,
                        past_events,
                    ]
                ),
                'chart_month_labels': json.dumps(
                    [item['month'].strftime('%b %Y') for item in monthly_stats if item['month']]
                ),
                'chart_month_totals': json.dumps([item['total'] for item in monthly_stats]),
                'dashboard_role': get_user_role(self.request.user),
            }
        )
        return context


@login_required
def export_registrations_csv(request):
    if get_user_role(request.user) != 'admin':
        messages.error(request, 'Only administrators can export registration data.')
        return redirect('dashboard:dashboard-home')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="event_registrations.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            'Registration ID',
            'Event ID',
            'Event Title',
            'Category',
            'Organizer Username',
            'Attendee Username',
            'Attendee Email',
            'Ticket Type',
            'Seat Count',
            'Registration Status',
            'Reminder Enabled',
            'Registered At',
            'Cancelled At',
        ]
    )

    registrations = Registration.objects.select_related('event', 'event__category', 'event__organizer', 'user', 'ticket')
    for registration in registrations:
        writer.writerow(
            [
                registration.id,
                registration.event_id,
                registration.event.title,
                registration.event.category.name,
                registration.event.organizer.username,
                registration.user.username,
                registration.user.email,
                registration.ticket.type,
                registration.seat_count,
                registration.status,
                registration.reminder_enabled,
                timezone.localtime(registration.registered_at).strftime('%Y-%m-%d %H:%M:%S'),
                timezone.localtime(registration.cancelled_at).strftime('%Y-%m-%d %H:%M:%S')
                if registration.cancelled_at
                else '',
            ]
        )

    return response
