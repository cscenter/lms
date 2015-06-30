from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.admin import UbereditorMixin
from htmlpages.forms import HtmlpageForm
from htmlpages.models import HtmlPage


class HtmlPageAdmin(TranslationAdmin, UbereditorMixin, admin.ModelAdmin):
    form = HtmlpageForm
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content', 'sites')}),
        (_('Advanced options'), {'classes': ('collapse',),
        'fields': ('registration_required', 'template_name')}),
    )
    list_display = ('url', 'title')
    list_filter = ('sites', 'registration_required')
    search_fields = ('url', 'title')

admin.site.register(HtmlPage, HtmlPageAdmin)
