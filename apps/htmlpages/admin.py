from __future__ import absolute_import, unicode_literals

from modeltranslation.admin import TranslationAdmin

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.widgets import AdminRichTextAreaWidget
from htmlpages.forms import HtmlpageForm
from htmlpages.models import HtmlPage


@admin.register(HtmlPage)
class HtmlPageAdmin(TranslationAdmin, admin.ModelAdmin):
    form = HtmlpageForm
    formfield_overrides = {
        models.TextField: {'widget': AdminRichTextAreaWidget},
    }
    fieldsets = (
        (None, {
            'fields': ('url', 'title', 'content', 'sites')
        }),
        (_('Advanced options'), {
            'classes': ('collapse',),
            'fields': ('registration_required', 'template_name')
        }),
    )
    list_display = ('url', 'title')
    list_filter = ('sites', 'registration_required')
    search_fields = ('url', 'title')
