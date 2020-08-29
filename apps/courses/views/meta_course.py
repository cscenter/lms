from django.conf import settings
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.models import Branch
from core.views import ProtectedFormMixin
from courses.forms import CourseForm
from courses.models import Course, MetaCourse
from courses.permissions import ChangeMetaCourse
from users.mixins import CuratorOnlyMixin

__all__ = ('MetaCourseDetailView', 'MetaCourseUpdateView')


class MetaCourseDetailView(generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "lms/courses/meta_detail.html"

    def get_context_data(self, **kwargs):
        filters = {}
        # Limit results on compsciclub.ru
        if hasattr(self.request, 'branch'):
            filters['main_branch'] = self.request.branch
        else:
            site_branches = Branch.objects.for_site(self.request.site.pk)
            filters['main_branch__in'] = [b.pk for b in site_branches]
        courses = (Course.objects
                   .filter(meta_course=self.object,
                           **filters)
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
