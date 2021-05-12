from django.contrib import admin

from notifications.models import Notification, Type


@admin.register(Type)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'code']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'recipient', 'emailed', 'timestamp']
    list_select_related = ('recipient', 'type')
