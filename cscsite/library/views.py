from __future__ import absolute_import, unicode_literals

from django.views.generic import ListView, DetailView

from .models import Book


class BookListView(ListView):
    context_object_name = "books"
    http_method_names = ["head", "get", "options"]
    queryset = Book.objects.select_related()


class BookDetailView(DetailView):
    context_object_name = "book"
    http_method_names = ["head", "get", "options"]
    model = Book
