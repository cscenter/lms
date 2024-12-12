from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from api.services import TokenService

from .models import ExternalServiceToken, Token


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('access_key', 'user', 'created', 'expire_at')
    fields = ('user', 'expire_at')
    ordering = ('-created',)
    raw_id_fields = ('user',)

    def save_model(self, request, obj, form, change):
        if obj.pk:
            super().save_model(request, obj, form, change)
        else:
            instance, secret_token = TokenService.create(
                obj.user, expire_at=obj.expire_at)
            for attr_name in ('pk', 'access_key', 'digest', 'expire_at'):
                setattr(obj, attr_name, getattr(instance, attr_name))
            msg = _("New secret token %s has been created. Save it somewhere "
                    "since you see it here for the last time.")
            messages.add_message(request, messages.WARNING, msg % secret_token)
            
@admin.register(ExternalServiceToken)
class ExternalServiceTokenAdmin(admin.ModelAdmin):
    list_display = ('service_tag', 'created')
    fields = ('service_tag', 'access_key')
    ordering = ('-created',)
    
    def get_readonly_fields(self, request, obj=None):
        return ['service_tag'] if obj else []
