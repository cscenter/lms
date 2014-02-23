from django.core.urlresolvers import reverse_lazy
from django.views import generic

from core.views import StudentOnlyMixin, TeacherOnlyMixin
from learning.models import Course
from learning.forms import CourseUpdateForm

class CourseTeacherListView(TeacherOnlyMixin, generic.ListView):
    model = Course
    template_name = "learning/courses_list_teacher.html"

    def get_queryset(self):
        return (Course.objects
                .filter(teachers=self.request.user)
                .order_by('-ongoing', 'name'))

class CourseUpdateView(TeacherOnlyMixin, generic.UpdateView):
    model = Course
    form_class = CourseUpdateForm
    template_name = "learning/courses_update.html"
    success_url = reverse_lazy('courses_teacher')

class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "learning/course_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super(CourseDetailView, self).get_context_data(*args, **kwargs)
        context['offerings'] = self.object.courseoffering_set.all()
        return context
