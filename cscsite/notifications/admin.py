from django.contrib import admin

from notifications.models import Type


class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'code']

admin.site.register(Type, NotificationTypeAdmin)
