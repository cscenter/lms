from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from courses.forms import MetaCourseForm
from courses.models import Course, CourseDurations, MetaCourse
from courses.permissions import EditMetaCourse

__all__ = ('MetaCourseDetailView', 'MetaCourseUpdateView')


class MetaCourseDetailView(LoginRequiredMixin, generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "lms/courses/meta_detail.html"

    def get_context_data(self, **kwargs):
        courses = (Course.objects
                   .filter(meta_course=self.object)
                   .available_on_site(self.request.site)
                   .select_related("meta_course", "semester", "main_branch")
                   .order_by('-semester__index'))
        context = {
            'meta_course': self.object,
            'courses': courses,
            'CourseDurations': CourseDurations
        }
        return context


class MetaCourseUpdateView(PermissionRequiredMixin, generic.UpdateView):
    permission_required = EditMetaCourse.name
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "courses/simple_crispy_form.html"
    form_class = MetaCourseForm
