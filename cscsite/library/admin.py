from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _

from core.admin import meta, urlize
from core.forms import AdminRichTextAreaWidget
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
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    @meta(_("read by"), allow_tags=True)
    def read_by_with_links(self, instance):
        return ", ".join(map(urlize, instance.read_by.all()))

admin.site.register(Book, BookAdmin)
