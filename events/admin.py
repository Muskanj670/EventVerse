from django.contrib import admin

from .models import Category, Event, Notification, Payment, Registration, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'organizer', 'city', 'start_date', 'status', 'price', 'capacity')
    list_filter = ('category', 'status', 'city', 'start_date', 'created_at')
    search_fields = ('title', 'description', 'venue', 'city', 'organizer__username', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_date'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('event', 'type', 'price', 'quantity')
    search_fields = ('event__title', 'type')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'ticket', 'status', 'registered_at')
    list_filter = ('status', 'registered_at')
    search_fields = ('user__username', 'event__title', 'ticket__type')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'event', 'amount', 'payment_method', 'status', 'paid_at')
    list_filter = ('status', 'payment_method', 'paid_at')
    search_fields = ('transaction_id', 'user__username', 'event__title')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
