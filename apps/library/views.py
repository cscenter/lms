from dal import autocomplete
from vanilla import DetailView, ListView

from auth.mixins import PermissionRequiredMixin
from learning.permissions import ViewLibrary
from users.mixins import CuratorOnlyMixin
from .models import Stock, Borrow, BookTag


class BookTagAutocomplete(CuratorOnlyMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = BookTag.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs.order_by('name')


class BookListView(PermissionRequiredMixin, ListView):
    context_object_name = "stocks"
    http_method_names = ["head", "get", "options"]
    template_name = "library/stock_list.html"
    permission_required = ViewLibrary.name

    def get_queryset(self):
        qs = (Stock.objects
              .select_related("branch", "book")
              .prefetch_related("borrows", "borrows__student"))
        # Students can see books from there branch only
        user = self.request.user
        if not user.is_curator:
            student_profile = user.get_student_profile(self.request.site)
            assert student_profile
            qs = qs.filter(branch_id=student_profile.branch_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["borrowed"] = set(Borrow.objects
                                  .filter(student=self.request.user)
                                  .values_list("stock_id", flat=True))
        return context


class BookDetailView(PermissionRequiredMixin, DetailView):
    context_object_name = "stock"
    http_method_names = ["head", "get", "options"]
    model = Stock
    permission_required = ViewLibrary.name

    def get_queryset(self):
        qs = (Stock.objects
              .select_related("book")
              .prefetch_related("borrows"))
        # Students can see books from there branch only
        user = self.request.user
        if not user.is_curator:
            student_profile = user.get_student_profile(self.request.site)
            assert student_profile
            qs = qs.filter(branch_id=student_profile.branch_id)
        return qs
