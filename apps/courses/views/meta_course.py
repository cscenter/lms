from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.models import Branch
from core.views import ProtectedFormMixin
from courses.forms import CourseForm
from courses.models import Course, MetaCourse
from courses.permissions import ChangeMetaCourse
from users.mixins import CuratorOnlyMixin

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
        }
        return context


class MetaCourseUpdateView(PermissionRequiredMixin, generic.UpdateView):
    permission_required = ChangeMetaCourse.name
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseForm
