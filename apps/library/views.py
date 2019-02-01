from vanilla import DetailView, ListView

from users.mixins import StudentOnlyMixin
from users.utils import get_student_city_code
from .models import Stock, Borrow


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
            city_code = get_student_city_code(self.request)
            qs = qs.filter(city_id=city_code)
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
            city_code = get_student_city_code(self.request)
            qs = qs.filter(city_id=city_code)
        return qs
