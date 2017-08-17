from __future__ import absolute_import, unicode_literals

from django.contrib import messages
from django.views import generic
from vanilla import DetailView, ListView

from core.exceptions import Redirect
from learning.viewmixins import StudentOnlyMixin
from learning.views.utils import get_student_city_code
from .models import Book, Stock, Borrow


# TODO: filter by city
class BookListView(StudentOnlyMixin, ListView):
    context_object_name = "stocks"
    http_method_names = ["head", "get", "options"]
    template_name = "library/stock_list.html"

    def get_queryset(self):
        qs = (Stock.objects
              .select_related("city", "book")
              .prefetch_related("borrows", "borrows__student"))
        # For students show books from the city of learning
        if not self.request.user.is_curator:
            try:
                city_code = get_student_city_code(self.request)
                qs = qs.filter(city_id=city_code)
            except ValueError as e:
                messages.error(self.request, e.args[0])
                raise Redirect(to="/")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["borrowed"] = set(Borrow.objects
                                  .filter(student=self.request.user)
                                  .values_list("stock_id", flat=True))
        return context


class BookDetailView(StudentOnlyMixin, DetailView):
    context_object_name = "stock"
    http_method_names = ["head", "get", "options"]
    model = Stock

    def get_queryset(self):
        qs = (Stock.objects
              .select_related("book")
              .prefetch_related("borrows"))
        # For students show books from the city of learning
        if not self.request.user.is_curator:
            try:
                city_code = get_student_city_code(self.request)
                qs = qs.filter(city_id=city_code)
            except ValueError as e:
                messages.error(self.request, e.args[0])
                raise Redirect(to="/")
        return qs
