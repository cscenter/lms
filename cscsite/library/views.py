from __future__ import absolute_import, unicode_literals

from django.views import generic

from core.views import StudentOnlyMixin
from .models import Book


class BookListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "books"
    http_method_names = ["head", "get", "options"]
    queryset = Book.objects.select_related()


class BookDetailView(StudentOnlyMixin, generic.DetailView):
    context_object_name = "book"
    http_method_names = ["head", "get", "options"]
    model = Book
