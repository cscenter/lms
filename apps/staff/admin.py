from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.db import models

from core.widgets import AdminRichTextAreaWidget
from staff.models import Hint


class HintAdmin(admin.ModelAdmin):
    list_display = ['question', 'sort']
    formfield_overrides = {
        models.TextField: {'widget': AdminRichTextAreaWidget},
    }

admin.site.register(Hint, HintAdmin)

