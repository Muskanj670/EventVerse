import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
        queryset = Event.objects.select_related('organizer', 'category')
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
        total_revenue = queryset.aggregate(total=Sum('price'))['total'] or 0
        confirmed_registrations = registrations.filter(status='confirmed').count()

        context.update(
            {
                'events': page_obj.object_list,
                'page_obj': page_obj,
                'paginator': paginator,
                'is_paginated': page_obj.has_other_pages(),
                'total_events': queryset.count(),
                'upcoming_events': queryset.filter(start_date__gte=now.date()).count(),
                'past_events': queryset.filter(end_date__lt=now.date()).count(),
                'this_month_events': queryset.filter(start_date__year=now.year, start_date__month=now.month).count(),
                'confirmed_registrations': confirmed_registrations,
                'estimated_revenue': total_revenue,
                'chart_category_labels': json.dumps(
                    [item['category__name'] for item in category_stats]
                ),
                'chart_category_totals': json.dumps([item['total'] for item in category_stats]),
                'chart_status_totals': json.dumps(
                    [
                        queryset.filter(start_date__gte=now.date()).count(),
                        queryset.filter(end_date__lt=now.date()).count(),
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
