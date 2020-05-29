from dal_select2_taggit.widgets import TaggitSelect2
from django import forms
from django.contrib import admin
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _
from taggit.admin import TagAdmin, TaggedItemInline

from core.admin import meta, BaseModelAdmin
from core.widgets import AdminRichTextAreaWidget
from .models import Book, Borrow, Stock, BookTag, TaggedBook


class BorrowInline(admin.TabularInline):
    # TODO: limit choices
    model = Borrow
    extra = 0
    raw_id_fields = ("student",)


class TaggedBookInline(TaggedItemInline):
    model = TaggedBook
    extra = 1
    raw_id_fields = ('content_object',)


class BookAdminForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'
        widgets = {
            'tags': TaggitSelect2(
                url='library_tags_autocomplete',
                attrs={"data-width": 'style'})
        }


@admin.register(BookTag)
class BookTagAdmin(TagAdmin):
    inlines = [TaggedBookInline]


@admin.register(Book)
class BookAdmin(BaseModelAdmin):
    form = BookAdminForm
    list_select_related = True
    list_display = ["author", "title"]
    list_display_links = ["author", "title"]
    list_filter = ["tags"]
    search_fields = ("title", "author")
    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }


@admin.register(Stock)
class StockAdmin(BaseModelAdmin):
    list_select_related = ['book', 'branch', 'branch__site']
    list_prefetch_related = ['borrows']
    list_display = ["book", "branch", "copies", "copies_left"]
    list_display_links = ["book"]
    autocomplete_fields = ["book"]
    list_filter = ["branch"]
    search_fields = ('book__title',)
    inlines = [BorrowInline]

    @meta(_("Copies available"))
    def copies_left(self, instance):
        return instance.available_copies


@admin.register(Borrow)
class BorrowAdmin(BaseModelAdmin):
    list_select_related = ['stock', 'stock__book', 'student']
    list_display = ('book_name', 'student', 'borrowed_on')
    list_filter = ('stock__branch',)
    search_fields = ('student__last_name', 'student__first_name',
                     'stock__book__title')
    raw_id_fields = ('stock', 'student')

    @meta(_("Book"))
    def book_name(self, obj):
        return obj.stock.book.title
