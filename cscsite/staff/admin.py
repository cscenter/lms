from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from core.admin import UbereditorMixin
from staff.models import Hint


class HintAdmin(UbereditorMixin, admin.ModelAdmin):
    list_display = ['question', 'sort']

admin.site.register(Hint, HintAdmin)

