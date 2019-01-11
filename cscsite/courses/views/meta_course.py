from django.views import generic

from core.utils import is_club_site
from core.views import ProtectedFormMixin
from courses.forms import CourseForm
from courses.models import Course, MetaCourse
from users.mixins import CuratorOnlyMixin

__all__ = ('MetaCourseDetailView', 'MetaCourseUpdateView')


class MetaCourseDetailView(generic.DetailView):
    model = MetaCourse
    template_name = "courses/meta_detail.html"
    context_object_name = 'meta_course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = (Course.objects
                   .select_related("meta_course", "semester", "city")
                   .filter(meta_course=self.object))
        # Separate by city only on compsciclub.ru
        if is_club_site():
            courses = courses.in_city(self.request.city_code)
        else:
            courses = courses.in_center_branches()
        context['courses'] = courses
        context["show_city"] = not is_club_site()
        return context


class MetaCourseUpdateView(CuratorOnlyMixin, ProtectedFormMixin,
                           generic.UpdateView):
    model = MetaCourse
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated and user.is_curator