from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _

from core.admin import meta, urlize, RelatedSpecMixin
from core.widgets import AdminRichTextAreaWidget
from .models import Book, Borrow, Stock


class BorrowInline(admin.TabularInline):
    # TODO: limit choices
    model = Borrow
    extra = 1


class BookAdmin(admin.ModelAdmin):
    list_display = ["author", "title"]
    list_display_links = ["author", "title"]
    list_filter = ["tags"]
    list_select_related = True
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


class StockAdmin(RelatedSpecMixin, admin.ModelAdmin):
    list_display = ["book", "city", "copies", "copies_left"]
    list_display_links = ["book"]
    list_filter = ["city"]
    list_select_related = ["book", "city"]
    inlines = [BorrowInline]
    related_spec = {
        'select': ['book', 'city'],
        'prefetch': ['borrows']
    }

    @meta(_("Copies available"))
    def copies_left(self, instance):
        return instance.available_copies


admin.site.register(Book, BookAdmin)
admin.site.register(Stock, StockAdmin)
