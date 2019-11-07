from django.conf import settings
from django.views import generic

from core.models import Branch
from core.views import ProtectedFormMixin
from courses.forms import CourseForm
from courses.models import Course, MetaCourse
from users.mixins import CuratorOnlyMixin

__all__ = ('MetaCourseDetailView', 'MetaCourseUpdateView')


class MetaCourseDetailView(generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "courses/meta_detail.html"
    context_object_name = 'meta_course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {}
        if hasattr(self.request, 'branch'):
            filters['branch'] = self.request.branch
        else:
            filters['branch__in'] = (Branch.objects
                                     .filter(site_id=settings.SITE_ID)
                                     .values_list('pk', flat=True))
        courses = (Course.objects
                   .filter(meta_course=self.object,
                           **filters)
                   .select_related("meta_course", "semester", "branch")
                   .order_by('-semester__index'))
        context['courses'] = courses
        return context


class MetaCourseUpdateView(CuratorOnlyMixin, ProtectedFormMixin,
                           generic.UpdateView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated and user.is_curator
