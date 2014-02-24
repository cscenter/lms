from django.core.urlresolvers import reverse_lazy
from django.views import generic

from braces.views import LoginRequiredMixin

from core.views import StudentOnlyMixin, TeacherOnlyMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseNews
from learning.forms import CourseUpdateForm

class CourseTeacherListView(TeacherOnlyMixin, generic.ListView):
    model = CourseOffering
    template_name = "learning/courses_list_teacher.html"

    def get_queryset(self):
        return (self.model.objects
                .filter(teachers=self.request.user)
                .order_by('semester__year', '-semester__type', 'course__name')
                .select_related('course', 'semester'))


class TimetableTeacherView(TeacherOnlyMixin, generic.ListView):
    model = CourseClass
    template_name = "learning/timetable_teacher.html"

    def get_queryset(self):
        return (self.model.objects
                .filter(course_offering__teachers=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue', 'course_offering',
                                'course_offering__course'))

    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableTeacherView, self)
                   .get_context_data(*args, **kwargs))
        return context


class CourseUpdateView(TeacherOnlyMixin, generic.UpdateView):
    model = Course
    form_class = CourseUpdateForm
    template_name = "learning/courses_update.html"
    success_url = reverse_lazy('courses_teacher')


class CourseDetailView(LoginRequiredMixin, generic.DetailView):
    model = Course
    template_name = "learning/course_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super(CourseDetailView, self).get_context_data(*args, **kwargs)
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class CourseClassDetailView(LoginRequiredMixin, generic.DetailView):
    model = CourseClass


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"
