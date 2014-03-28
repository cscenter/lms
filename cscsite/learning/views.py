from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils.translation import ugettext_lazy as _

from braces.views import LoginRequiredMixin

from core.views import StudentOnlyMixin, TeacherOnlyMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews, Enrollment, Semester, \
    Assignment, AssignmentStudent, AssignmentComment
from learning.forms import CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm, \
    CourseClassForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm

import utils

class TimetableMixin(object):
    model = CourseClass
    template_name = "learning/timetable.html"

    def get_queryset(self):
        semester_qstr = self.request.GET.get('semester')
        self.semester_pair = self._split_semester(semester_qstr)
        if not self.semester_pair:
            self.semester_pair = utils.get_current_semester_pair()
        return (CourseClass.by_semester(self.semester_pair)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    # TODO: test "pagination"
    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableMixin, self)
                   .get_context_data(*args, **kwargs))
        year, season = self.semester_pair
        p, n = utils.get_prev_next_semester_pairs(self.semester_pair)
        p_year, p_season = p
        n_year, n_season = n
        context['next_semester'] = "{0}_{1}".format(n_year, n_season)
        context['previous_semester'] = "{0}_{1}".format(p_year, p_season)
        context['current_semester_obj'] = Semester(year=year, type=season)
        context['timetable_type'] = self.timetable_type
        return context

    def _split_semester(self, semester_string):
        if not semester_string:
            return None
        pair = semester_string.strip().split("_")
        if not len(pair) == 2:
            return None
        try:
            return (int(pair[0]), pair[1])
        except ValueError:
            return None


class TimetableTeacherView(TimetableMixin,
                           TeacherOnlyMixin,
                           generic.ListView):
    timetable_type = 'teacher'

    def get_queryset(self):
        return (super(TimetableTeacherView, self).get_queryset()
                .filter(course_offering__teachers=self.request.user))


class TimetableStudentView(TimetableMixin,
                           StudentOnlyMixin,
                           generic.ListView):
    timetable_type = 'student'

    def get_queryset(self):
        return (super(TimetableStudentView, self).get_queryset()
                .filter(course_offering__enrolled_students=self.request.user))


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

    def get_initial(self, *args, **kwargs):
        initial = (super(CourseClassCreateUpdateMixin, self)
                   .get_initial(*args, **kwargs))
        if self.request.GET.get('back') == 'course_offering':
            pk = self.request.GET['course_offering']
            try:
                pk = int(pk)
            except ValueError:
                raise Http404
            self.course_offering = get_object_or_404(
                CourseOffering.objects.filter(pk=pk))
            initial['course_offering'] = self.course_offering
        return initial

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_success_url(self):
        if self.request.GET.get('back') == 'timetable':
            return reverse('timetable_teacher')
        if self.request.GET.get('back') == 'course_offering':
            return self.course_offering.get_absolute_url()
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


class AssignmentListMixin(object):
    model = AssignmentStudent
    template_name = "learning/assignment_list.html"
    context_object_name = 'assignment_list'

    def get_queryset(self):
        return (self.model.objects
                .order_by('assignment__deadline_at',
                          'assignment__course_offering__course__name')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentListMixin, self)
                   .get_context_data(*args, **kwargs))
        open_, archive = utils.split_list(lambda a_s: a_s.assignment.is_open,
                                          context['assignment_list'])
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['list_type'] = self.list_type
        return context


class AssignmentStudentListView(StudentOnlyMixin,
                                AssignmentListMixin,
                                generic.ListView):
    list_type = 'student'

    def get_queryset(self):
        return (super(AssignmentStudentListView, self).get_queryset()
                .filter(student=self.request.user))


class AssignmentTeacherListView(TeacherOnlyMixin,
                                AssignmentListMixin,
                                generic.ListView):
    list_type = 'teacher'

    def get_queryset(self):
        base_qs = (super(AssignmentTeacherListView, self).get_queryset()
                   .filter(assignment__course_offering__teachers=
                           self.request.user))
        if self.request.GET.get('only_ungraded') == 'true':
            return base_qs.filter(state__in=['not_checked',
                                             'being_checked'])
        else:
            return base_qs

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherListView, self)
                   .get_context_data(*args, **kwargs))
        context['only_ungraded'] = (self.request.GET.get('only_ungraded')
                                    == 'true')
        return context



class AssignmentDetailMixin(object):
    model = AssignmentComment
    template_name = "learning/assignment_detail.html"
    form_class = AssignmentCommentForm

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentDetailMixin, self)
                   .get_context_data(*args, **kwargs))
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(
            AssignmentStudent
            .objects
            .filter(pk=pk)
            .select_related('assignment',
                            'student',
                            'assignment__course_offering',
                            'assignment__course_offering__course',
                            'assignment__course_offering__semester')
            .prefetch_related('assignment__course_offering__teachers'))
        context['a_s'] = a_s
        context['comments'] = (AssignmentComment.objects
                               .filter(assignment_student=a_s)
                               .order_by('created'))
        context['one_teacher'] = (a_s
                                  .assignment
                                  .course_offering
                                  .teachers
                                  .count() == 1)
        context['user_type'] = self.user_type
        return context

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(AssignmentStudent.objects.filter(pk=pk))
        comment = form.save(commit=False)
        comment.assignment_student = a_s
        comment.author = self.request.user
        comment.save()
        if self.user_type == 'student':
            url = reverse('assignment_detail_student', args=[a_s.pk])
        elif self.user_type == 'teacher':
            url = reverse('assignment_detail_teacher', args=[a_s.pk])
        return redirect(url)


class AssignmentStudentDetailView(StudentOnlyMixin,
                                  AssignmentDetailMixin,
                                  generic.CreateView):
    user_type = 'student'


class AssignmentTeacherDetailView(TeacherOnlyMixin,
                                  AssignmentDetailMixin,
                                  generic.CreateView):
    user_type = 'teacher'

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))
        initial = {'state': context['a_s'].state}
        context['grade_form'] = AssignmentGradeForm(initial)
        return context

    def post(self, request, *args, **kwargs):
        if 'grading_form' in request.POST:
            form = AssignmentGradeForm(request.POST)
            pk = self.kwargs.get('pk')
            a_s = get_object_or_404(AssignmentStudent.objects.filter(pk=pk))
            if form.is_valid():
                a_s.state = form.cleaned_data['state']
                a_s.save()
                return redirect(reverse('assignment_detail_teacher', args=[pk]))
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid")+
                                              form.errors)
        else:
            return (super(AssignmentTeacherDetailView, self)
                    .post(request, *args, **kwargs))


class AssignmentCreateUpdateMixin(object):
    model = Assignment
    template_name = "learning/simple_crispy_form.html"
    form_class = AssignmentForm

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse('assignment_detail_teacher', args=[self.object.pk])


class AssignmentCreateView(TeacherOnlyMixin,
                           AssignmentCreateUpdateMixin,
                           generic.CreateView):
    pass


class AssignmentUpdateView(TeacherOnlyMixin,
                           AssignmentCreateUpdateMixin,
                           generic.UpdateView):
    pass


class AssignmentDeleteView(TeacherOnlyMixin,
                           generic.DeleteView):
    model = Assignment
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return reverse('assignment_list_teacher')
