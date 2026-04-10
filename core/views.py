from django.db.models import Q
from django.views.generic import ListView, TemplateView

from events.models import Category, Event


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_events'] = Event.objects.select_related('organizer', 'category').filter(status='published')[:6]
        context['categories'] = Category.objects.all()
        return context


class SearchView(ListView):
    model = Event
    template_name = 'core/search_results.html'
    context_object_name = 'events'
    paginate_by = 6

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        queryset = Event.objects.select_related('organizer', 'category').filter(status='published')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context
