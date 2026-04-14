from django.urls import path

from .views import DashboardView, export_registrations_csv

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard-home'),
    path('registrations/export/', export_registrations_csv, name='export-registrations'),
]
