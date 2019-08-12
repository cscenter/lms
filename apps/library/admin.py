from django.contrib import admin
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _

from core.admin import meta, urlize, RelatedSpecMixin
from core.widgets import AdminRichTextAreaWidget
from .models import Book, Borrow, Stock


class BorrowInline(admin.TabularInline):
    # TODO: limit choices
    model = Borrow
    extra = 0
    raw_id_fields = ("student",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["author", "title"]
    list_display_links = ["author", "title"]
    list_filter = ["tags"]
    list_select_related = True
    search_fields = ("title", "author")
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


@admin.register(Stock)
class StockAdmin(RelatedSpecMixin, admin.ModelAdmin):
    list_display = ["book", "branch", "copies", "copies_left"]
    list_display_links = ["book"]
    autocomplete_fields = ["book"]
    list_filter = ["branch"]
    inlines = [BorrowInline]
    related_spec = {
        'select': ['book', 'branch'],
        'prefetch': ['borrows']
    }

    @meta(_("Copies available"))
    def copies_left(self, instance):
        return instance.available_copies


@admin.register(Borrow)
class BorrowAdmin(admin.ModelAdmin):
    list_display = ('stock', 'student', 'borrowed_on')
    list_filter = ('stock__branch',)
    raw_id_fields = ('stock', 'student')

