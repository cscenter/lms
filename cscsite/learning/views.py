from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import generic

from braces.views import LoginRequiredMixin

from core.views import StudentOnlyMixin, TeacherOnlyMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews
from learning.forms import CourseUpdateForm, CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm

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
                .filter(cscuser__enrolled_on=self.request.user))


class CourseDetailView(LoginRequiredMixin, generic.DetailView):
    model = Course
    template_name = "learning/course_detail.html"
    context_object_name = 'course'

    def get_context_data(self, *args, **kwargs):
        context = super(CourseDetailView, self).get_context_data(*args, **kwargs)
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class GetCourseOfferingObjectMixin:
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
                                   .enrolled_on
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
        self.request.user.enrolled_on.add(course_offering)
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
        self.request.user.enrolled_on.remove(course_offering)
        return redirect('course_offering_detail',
                        course_slug=course_offering.course.slug,
                        semester_slug=course_offering.semester.slug)


class CourseClassDetailView(LoginRequiredMixin, generic.DetailView):
    model = CourseClass


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"
