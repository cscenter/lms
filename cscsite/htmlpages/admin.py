from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from core.admin import UbereditorMixin


class ExtendedFlatPageAdmin(UbereditorMixin, FlatPageAdmin):
    pass

admin.site.unregister(FlatPage)
admin.site.register(FlatPage, ExtendedFlatPageAdmin)
