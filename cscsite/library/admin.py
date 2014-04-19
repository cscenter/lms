from __future__ import absolute_import, unicode_literals

from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from pagedown.widgets import AdminPagedownWidget

from core.admin import meta, urlize
from .models import Book, Borrow


class BorrowInline(admin.TabularInline):
    model = Borrow
    extra = 1


class BookAdmin(admin.ModelAdmin):
    list_display = ["author", "title", "read_by_with_links"]
    list_display_links = ["author", "title"]
    list_filter = ["tags"]
    list_select_related = True

    inlines = [BorrowInline]
    formfield_overrides = {
        models.TextField: {'widget': AdminPagedownWidget}
    }

    @meta(_("read by"), allow_tags=True)
    def read_by_with_links(self, instance):
        return ", ".join(map(urlize, instance.read_by.all()))

admin.site.register(Book, BookAdmin)
