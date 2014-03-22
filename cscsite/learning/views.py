from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import generic

from braces.views import LoginRequiredMixin

from core.views import StudentOnlyMixin, TeacherOnlyMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews, Enrollment, \
    Assignment, AssignmentStudent
from learning.forms import CourseUpdateForm, CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm, \
    CourseClassForm

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


class CourseListView(generic.ListView):
    model = CourseOffering
    template_name = "learning/courses_list.html"
    context_object_name = 'course_list'

    list_type = 'all'

    def get_queryset(self):
        return (self.model.objects
                .order_by('semester__year', '-semester__type', 'course__name')
                .select_related('course', 'semester')
                .prefetch_related('teachers'))

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseListView, self)
                   .get_context_data(*args, **kwargs))
        ongoing, archive = [], []
        for course in context['course_list']:
            if course.is_ongoing:
                ongoing.append(course)
            else:
                archive.append(course)
        context['course_list_ongoing'] = ongoing
        context['course_list_archive'] = archive
        context['list_type'] = self.list_type
        return context


class CourseTeacherListView(TeacherOnlyMixin, CourseListView):
    list_type = 'teaching'

    def get_queryset(self):
        return (super(CourseTeacherListView, self)
                .get_queryset()
                .filter(teachers=self.request.user))


class CourseStudentListView(StudentOnlyMixin, CourseListView):
    list_type = 'learning'

    def get_queryset(self):
        return (super(CourseStudentListView, self)
                .get_queryset()
                .filter(enrolled_students=self.request.user))


class CourseDetailView(LoginRequiredMixin, generic.DetailView):
    model = Course
    template_name = "learning/course_detail.html"
    context_object_name = 'course'

    def get_context_data(self, *args, **kwargs):
        context = super(CourseDetailView, self).get_context_data(*args, **kwargs)
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class GetCourseOfferingObjectMixin(object):
    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-")
        return get_object_or_404(
            self.model.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug'])
            .select_related('course', 'semester')
            .prefetch_related('teachers',
                              'courseclass_set',
                              'courseofferingnews_set'))


class CourseOfferingDetailView(LoginRequiredMixin,
                               GetCourseOfferingObjectMixin,
                               generic.DetailView):
    model = CourseOffering
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_enrolled'] = (self.request.user.is_student and
                                  (self.request.user
                                   .enrolled_on_set
                                   .filter(pk=self.object.pk)
                                   .exists()))
        return context


class CourseOfferingEditDescrView(TeacherOnlyMixin,
                                  GetCourseOfferingObjectMixin,
                                  generic.UpdateView):
    model = CourseOffering
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingEditDescrForm


class CourseOfferingNewsCreateView(TeacherOnlyMixin,
                                   generic.CreateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def form_valid(self, form):
        year, semester_type = self.kwargs['semester_slug'].split("-")
        course_offering = get_object_or_404(
            CourseOffering.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug']))
        form.instance.course_offering = course_offering
        self.success_url = course_offering.get_absolute_url()
        return super(CourseOfferingNewsCreateView, self).form_valid(form)


class CourseOfferingNewsUpdateView(TeacherOnlyMixin,
                                   generic.UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()


class CourseOfferingNewsDeleteView(TeacherOnlyMixin,
                                   generic.DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()


class CourseOfferingEnrollView(generic.FormView):
    http_method_names = ['post']
    form_class = CourseOfferingPKForm

    def form_valid(self, form):
        course_offering = get_object_or_404(
            CourseOffering.objects.filter(
                pk=form.cleaned_data['course_offering_pk']))
        Enrollment(student=self.request.user,
                   course_offering=course_offering).save()
        return redirect('course_offering_detail',
                        course_slug=course_offering.course.slug,
                        semester_slug=course_offering.semester.slug)


class CourseOfferingUnenrollView(generic.FormView):
    http_method_names = ['post']
    form_class = CourseOfferingPKForm

    def form_valid(self, form):
        course_offering = get_object_or_404(
            CourseOffering.objects.filter(
                pk=form.cleaned_data['course_offering_pk']))
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=self.request.user,
                                      course_offering=course_offering))
        enrollment.delete()
        return redirect('course_offering_detail',
                        course_slug=course_offering.course.slug,
                        semester_slug=course_offering.semester.slug)


class CourseClassDetailView(LoginRequiredMixin, generic.DetailView):
    model = CourseClass


class CourseClassCreateUpdateMixin(object):
    model = CourseClass
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseClassForm

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_success_url(self):
        if self.request.GET.get('back') == 'timetable':
            return reverse('timetable_teacher')
        else:
            return super(CourseClassCreateUpdateMixin, self).get_success_url()


class CourseClassCreateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin,
                            generic.CreateView):
    pass


class CourseClassUpdateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin,
                            generic.UpdateView):
    pass


class CourseClassDeleteView(TeacherOnlyMixin, generic.DeleteView):
    model = CourseClass
    template_name = "learning/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"


class AssignmentStudentListView(StudentOnlyMixin, generic.ListView):
    model = AssignmentStudent
    template_name = "learning/assignment_list.html"
    context_object_name = 'assignment_list'

    def get_queryset(self):
        return (self.model.objects
                .filter(student=self.request.user)
                .order_by('assignment__deadline',
                          'assignment__course_offering__course__name')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentStudentListView, self)
                   .get_context_data(*args, **kwargs))
        open_assignments, archive = [], []
        for assignment_student in context['assignment_list']:
            if assignment_student.assignment.open:
                open_assignments.append(assignment_student)
            else:
                archive.append(assignment_student)
        archive.reverse()
        context['assignment_list_open'] = open_assignments
        context['assignment_list_archive'] = archive
        return context
