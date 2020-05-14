from vanilla import DetailView, ListView

from auth.mixins import PermissionRequiredMixin
from .models import Stock, Borrow


class BookListView(PermissionRequiredMixin, ListView):
    context_object_name = "stocks"
    http_method_names = ["head", "get", "options"]
    template_name = "library/stock_list.html"
    permission_required = "study.view_library"

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
    permission_required = "study.view_library"

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
