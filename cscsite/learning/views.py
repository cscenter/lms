from __future__ import absolute_import, unicode_literals

import datetime
from calendar import Calendar
from collections import OrderedDict, defaultdict
import os

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from braces.views import LoginRequiredMixin
from dateutil.relativedelta import relativedelta

from core.views import StudentOnlyMixin, TeacherOnlyMixin, StaffOnlyMixin, \
    ProtectedFormMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews, Enrollment, \
    Assignment, AssignmentStudent, AssignmentComment, \
    CourseClassAttachment
from learning.forms import CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm, \
    CourseClassForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm

from . import utils


class TimetableMixin(object):
    model = CourseClass
    template_name = "learning/timetable.html"

    def __init__(self, *args, **kwargs):
        self._context_weeks = None
        super(TimetableMixin, self).__init__(*args, **kwargs)

    def get_queryset(self):
        week_qstr = self.request.GET.get('week')
        year_qstr = self.request.GET.get('year')
        try:
            week = int(week_qstr)
            year = int(year_qstr)
        except TypeError:
            # This returns current week number. Beware: the week's number
            # is as of ISO8601, so 29th of December can be reported as
            # 1st week of the next year.
            year, week, _ = now().date().isocalendar()
        start = utils.iso_to_gregorian(year, week, 1)
        end = utils.iso_to_gregorian(year, week, 7)
        next_w_cal = (start + datetime.timedelta(weeks=1)).isocalendar()
        prev_w_cal = (start + datetime.timedelta(weeks=-1)).isocalendar()
        self._context_weeks = {'week': week,
                               'week_start': start,
                               'week_end': end,
                               'month': start.month,
                               'year': year,
                               'prev_year': prev_w_cal[0],
                               'prev_week': prev_w_cal[1],
                               'next_year': next_w_cal[0],
                               'next_week': next_w_cal[1]}
        return (CourseClass.objects
                .filter(date__range=[start, end])
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    # TODO: test "pagination"
    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableMixin, self)
                   .get_context_data(*args, **kwargs))
        context.update(self._context_weeks)
        context['user_type'] = self.user_type
        return context


class TimetableTeacherView(TeacherOnlyMixin,
                           TimetableMixin,
                           generic.ListView):
    user_type = 'teacher'

    def get_queryset(self):
        return (super(TimetableTeacherView, self).get_queryset()
                .filter(course_offering__teachers=self.request.user))


class TimetableStudentView(StudentOnlyMixin,
                           TimetableMixin,
                           generic.ListView):
    user_type = 'student'

    def get_queryset(self):
        return (super(TimetableStudentView, self).get_queryset()
                .filter(course_offering__enrolled_students=self.request.user))


class CalendarMixin(object):
    model = CourseClass
    template_name = "learning/calendar.html"

    def __init__(self, *args, **kwargs):
        self._month_date = None
        super(CalendarMixin, self).__init__(*args, **kwargs)

    def get_queryset(self):
        year_qstr = self.request.GET.get('year')
        month_qstr = self.request.GET.get('month')
        try:
            year = int(year_qstr)
            month = int(month_qstr)
        except TypeError:
            today = now().date()
            year, month = today.year, today.month
        self._month_date = datetime.date(year=year, month=month, day=1)
        prev_month_date = self._month_date + relativedelta(months=-1)
        next_month_date = self._month_date + relativedelta(months=+1)
        return (CourseClass.objects
                .filter(Q(date__month=month,
                          date__year=year)
                        | Q(date__month=prev_month_date.month,
                            date__year=prev_month_date.year)
                        | Q(date__month=next_month_date.month,
                            date__year=next_month_date.year))
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    # TODO: test "pagination"
    def get_context_data(self, *args, **kwargs):
        context = (super(CalendarMixin, self)
                   .get_context_data(*args, **kwargs))
        context['next_date'] = self._month_date + relativedelta(months=1)
        context['prev_date'] = self._month_date + relativedelta(months=-1)
        context['user_type'] = self.user_type

        classes = context['object_list']
        dates_to_classes = defaultdict(list)
        for course_class in classes:
            dates_to_classes[course_class.date].append(course_class)

        cal = Calendar(0)

        month_cal = cal.monthdatescalendar(self._month_date.year,
                                           self._month_date.month)
        month = [(week[0].isocalendar()[1],
                  [(day, dates_to_classes[day],
                    day.month == self._month_date.month)
                   for day in week])
                 for week in month_cal]

        context['month'] = month
        context['month_date'] = self._month_date
        return context


class CalendarTeacherView(TeacherOnlyMixin,
                          CalendarMixin,
                          generic.ListView):
    user_type = 'teacher'

    def get_queryset(self):
        return (super(CalendarTeacherView, self).get_queryset()
                .filter(course_offering__teachers=self.request.user))


class CalendarStudentView(CalendarMixin,
                          generic.ListView):
    user_type = "student"

    def get_queryset(self):
        return (super(CalendarStudentView, self).get_queryset()
                .filter(course_offering__enrolled_students=self.request.user))


class CalendarFullView(LoginRequiredMixin,
                       CalendarMixin,
                       generic.ListView):
    user_type = 'full'


class CourseListMixin(object):
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
        context = (super(CourseListMixin, self)
                   .get_context_data(*args, **kwargs))
        ongoing, archive = utils.split_list(context['course_list'],
                                            lambda course: course.is_ongoing)
        context['course_list_ongoing'] = ongoing
        context['course_list_archive'] = archive
        context['list_type'] = self.list_type
        return context


class CourseListView(CourseListMixin, generic.ListView):
    model = CourseOffering
    template_name = "learning/courses_list_all.html"


class CourseTeacherListView(TeacherOnlyMixin,
                            CourseListMixin,
                            generic.ListView):
    template_name = "learning/courses_list_teacher.html"

    def get_queryset(self):
        return (super(CourseTeacherListView, self)
                .get_queryset()
                .filter(teachers=self.request.user))


class CourseStudentListView(StudentOnlyMixin,
                            CourseListMixin,
                            generic.ListView):
    template_name = "learning/courses_list_student.html"

    def get_queryset(self):
        return (CourseOffering
                .by_semester(utils.get_current_semester_pair())
                .order_by('semester__year', '-semester__type', 'course__name')
                .select_related('course', 'semester')
                .prefetch_related('teachers', 'enrolled_students'))

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseStudentListView, self)
                   .get_context_data(*args, **kwargs))
        ongoing, available = utils.split_list(
            context['course_list'],
            lambda c_o: self.request.user in c_o.enrolled_students.all())
        context['course_list_ongoing'] = ongoing
        context['course_list_available'] = available
        return context


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "learning/course_detail.html"
    context_object_name = 'course'

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class GetCourseOfferingObjectMixin(object):
    model = CourseOffering

    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        return get_object_or_404(
            self.model.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug'])
            .select_related('course',
                            'semester')
            .prefetch_related('teachers',
                              'courseclass_set',
                              'courseofferingnews_set',
                              'assignment_set'))


class CourseOfferingDetailView(GetCourseOfferingObjectMixin,
                               generic.DetailView):
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_enrolled'] = (self.request.user.is_authenticated() and
                                  self.request.user.is_student and
                                  (self.request.user
                                   .enrolled_on_set
                                   .filter(pk=self.object.pk)
                                   .exists()))
        context['is_actual_teacher'] = (
            self.request.user.is_authenticated() and
            self.request.user in self.object.teachers.all())
        return context


class CourseOfferingEditDescrView(TeacherOnlyMixin,
                                  ProtectedFormMixin,
                                  GetCourseOfferingObjectMixin,
                                  generic.UpdateView):
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingEditDescrForm

    def is_form_allowed(self, user, obj):
        return user in obj.teachers.all()


class CourseOfferingNewsCreateView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.CreateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseOfferingNewsCreateView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        form.instance.course_offering = self._course_offering
        self.success_url = self._course_offering.get_absolute_url()
        return super(CourseOfferingNewsCreateView, self).form_valid(form)

    def is_form_allowed(self, user, obj):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        self._course_offering = get_object_or_404(
            CourseOffering.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug']))
        return user in self._course_offering.teachers.all()


class CourseOfferingNewsUpdateView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user in obj.course_offering.teachers.all()


class CourseOfferingNewsDeleteView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user in obj.course_offering.teachers.all()


class CourseOfferingEnrollView(StudentOnlyMixin, generic.FormView):
    http_method_names = ['post']
    form_class = CourseOfferingPKForm

    def form_valid(self, form):
        course_offering = get_object_or_404(
            CourseOffering.objects.filter(
                pk=form.cleaned_data['course_offering_pk']))
        Enrollment(student=self.request.user,
                   course_offering=course_offering).save()
        if self.request.POST.get('back') == 'course_list_student':
            return redirect('course_list_student')
        else:
            return redirect('course_offering_detail',
                            course_slug=course_offering.course.slug,
                            semester_slug=course_offering.semester.slug)


class CourseOfferingUnenrollView(StudentOnlyMixin, generic.DeleteView):
    template_name = "learning/simple_delete_confirmation.html"

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseOfferingUnenrollView, self).__init__(*args, **kwargs)

    def get_object(self, _=None):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        course_offering = get_object_or_404(
            CourseOffering.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug']))
        self._course_offering = course_offering
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=self.request.user,
                                      course_offering=course_offering))
        return enrollment

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingUnenrollView, self)
                   .get_context_data(*args, **kwargs))
        context['confirmation_text'] = (
            _("Are you sure you want to unenroll "
              "from \"%(course)s\"?")
            % {'course': self.object.course_offering})
        context['confirmation_button_text'] = _("Unenroll")
        return context

    def get_success_url(self):
        if self.request.GET.get('back') == 'course_list_student':
            return reverse('course_list_student')
        else:
            c_o = self._course_offering
            return reverse('course_offering_detail',
                           kwargs={"course_slug": c_o.course.slug,
                                   "semester_slug": c_o.semester.slug})


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseClassDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_actual_teacher'] = (
            self.request.user.is_authenticated() and
            self.request.user in (self.object
                                  .course_offering
                                  .teachers.all()))
        context['attachments'] = self.object.courseclassattachment_set.all()
        return context


class CourseClassCreateUpdateMixin(object):
    model = CourseClass
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseClassForm

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseClassCreateUpdateMixin, self).__init__(*args, **kwargs)

    def get_initial(self, *args, **kwargs):
        initial = (super(CourseClassCreateUpdateMixin, self)
                   .get_initial(*args, **kwargs))
        if self.request.GET.get('back') == 'course_offering':
            pk = self.request.GET['course_offering']
            try:
                pk = int(pk)
            except ValueError:
                raise Http404
            self._course_offering = get_object_or_404(
                CourseOffering.objects.filter(pk=pk))
            initial['course_offering'] = self._course_offering
        return initial

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            if self.object:
                # It's an update, we should remove old attachments
                old_attachments = (CourseClassAttachment.objects
                                   .filter(course_class=self.object))
                for attachment in old_attachments:
                    os.remove(attachment.material.path)
                    attachment.delete()
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()

        return super(CourseClassCreateUpdateMixin, self).form_valid(form)

    def get_success_url(self):
        if self.request.GET.get('back') == 'timetable':
            return reverse('timetable_teacher')
        if self.request.GET.get('back') == 'course_offering':
            return self._course_offering.get_absolute_url()
        if self.request.GET.get('back') == 'calendar':
            return reverse('calendar_teacher')
        else:
            return super(CourseClassCreateUpdateMixin, self).get_success_url()


## No ProtectedFormMixin here because we are filtering out other's courses
## on form level (see __init__ of CourseClassForm)
class CourseClassCreateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin,
                            generic.CreateView):
    pass


## Same here
class CourseClassUpdateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin,
                            generic.UpdateView):
    pass


class CourseClassDeleteView(TeacherOnlyMixin,
                            ProtectedFormMixin,
                            generic.DeleteView):
    model = CourseClass
    template_name = "learning/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')

    def is_form_allowed(self, user, obj):
        return user in obj.course_offering.teachers.all()


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"


class AssignmentStudentListView(StudentOnlyMixin,
                                generic.ListView):
    model = AssignmentStudent
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_student.html"
    user_type = 'student'

    def get_queryset(self):
        return (self.model.objects
                .filter(student=self.request.user)
                .order_by('assignment__deadline_at',
                          'assignment__course_offering__course__name',
                          'pk')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentStudentListView, self)
                   .get_context_data(*args, **kwargs))
        open_, archive = utils.split_list(context['assignment_list'],
                                          lambda a_s: a_s.assignment.is_open)
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['user_type'] = self.user_type
        return context


class AssignmentTeacherListView(TeacherOnlyMixin,
                                generic.ListView):
    model = AssignmentStudent
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_teacher.html"
    user_type = 'teacher'

    def get_queryset(self):
        base_qs = (self.model.objects
                   .filter(assignment__course_offering__teachers=
                           self.request.user)
                   .order_by('assignment__deadline_at',
                             'assignment__course_offering__course__name',
                             'pk')
                   .select_related('assignment',
                                   'assignment__course_offering',
                                   'assignment__course_offering__course',
                                   'assignment__course_offering__semester',
                                   'student'))
        if self.request.GET.get('only_ungraded') == 'true':
            return base_qs.filter(state__in=AssignmentStudent.OPEN_STATES)
        else:
            return base_qs

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherListView, self)
                   .get_context_data(*args, **kwargs))
        open_ = [a_s
                 for a_s in context['assignment_list']
                 if (a_s.assignment.is_open or
                     a_s.state in AssignmentStudent.OPEN_STATES)]
        archive = (Assignment.objects
                   .filter(course_offering__teachers=self.request.user)
                   .order_by('deadline_at',
                             'course_offering__course__name',
                             'pk')
                   .select_related('course_offering',
                                   'course_offering__course',
                                   'course_offering__semester'))
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['user_type'] = self.user_type
        context['only_ungraded'] = \
            (self.request.GET.get('only_ungraded') == 'true')
        return context


class AssignmentTeacherDetailView(TeacherOnlyMixin,
                                  generic.DetailView):
    model = Assignment
    template_name = "learning/assignment_detail.html"
    context_object_name = 'assignment'

    def get_queryset(self):
        return (self.model.objects
                .select_related('course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['a_s_list'] = \
            (AssignmentStudent.objects
             .filter(assignment__pk=self.object.pk)
             .select_related('assignment',
                             'assignment__course_offering',
                             'assignment__course_offering__course',
                             'assignment__course_offering__semester',
                             'student'))
        return context


class AssignmentStudentDetailMixin(object):
    model = AssignmentComment
    template_name = "learning/assignment_student_detail.html"
    form_class = AssignmentCommentForm

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentStudentDetailMixin, self)
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

        # This should guard against reading other's assignments. Not generic
        # enough, but can't think of better way
        if (self.user_type == 'student'
                and not a_s.student == self.request.user):
            raise PermissionDenied

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
            url = reverse('a_s_detail_student', args=[a_s.pk])
        elif self.user_type == 'teacher':
            url = reverse('a_s_detail_teacher', args=[a_s.pk])
        else:
            raise AssertionError
        return redirect(url)


# shitty name :(
class ASStudentDetailView(StudentOnlyMixin,
                          AssignmentStudentDetailMixin,
                          generic.CreateView):
    user_type = 'student'


class ASTeacherDetailView(TeacherOnlyMixin,
                          AssignmentStudentDetailMixin,
                          generic.CreateView):
    user_type = 'teacher'

    def get_context_data(self, *args, **kwargs):
        context = (super(ASTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))
        a_s = context['a_s']
        initial = {'state': a_s.state}
        context['is_actual_teacher'] = (
            self.request.user in (a_s
                                  .assignment
                                  .course_offering
                                  .teachers.all()))
        context['grade_form'] = AssignmentGradeForm(initial)
        base = (AssignmentStudent.objects
                .filter(state='not_checked')
                .order_by('assignment__deadline_at',
                          'assignment__course_offering__course__name',
                          'pk'))
        next_a_s = (base.filter(pk__gt=a_s.pk).first() or
                    base.filter(pk__lt=a_s.pk).first())
        context['next_a_s_pk'] = next_a_s.pk if next_a_s else None
        return context

    def post(self, request, *args, **kwargs):
        if 'grading_form' in request.POST:
            form = AssignmentGradeForm(request.POST)
            pk = self.kwargs.get('pk')
            a_s = get_object_or_404(AssignmentStudent.objects.filter(pk=pk))

            # Too hard to use ProtectedFormMixin here, let's just inline it's
            # logic. A little drawback is that teachers still can leave
            # comments under other's teachers assignments, but can not grade,
            # so it's acceptible, IMO.
            teachers = a_s.assignment.course_offering.teachers.all()
            if request.user not in teachers:
                raise PermissionDenied

            if form.is_valid():
                a_s.state = form.cleaned_data['state']
                a_s.save()
                return redirect(reverse('a_s_detail_teacher',
                                        args=[pk]))
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              form.errors)
        else:
            return (super(ASTeacherDetailView, self)
                    .post(request, *args, **kwargs))


class AssignmentCreateUpdateMixin(object):
    model = Assignment
    template_name = "learning/simple_crispy_form.html"
    form_class = AssignmentForm
    success_url = reverse_lazy('assignment_list_teacher')

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())


## No ProtectedFormMixin here because we are filtering out other's courses
## on form level (see __init__ of AssignmentForm)
class AssignmentCreateView(TeacherOnlyMixin,
                           AssignmentCreateUpdateMixin,
                           generic.CreateView):
    pass


## Same here
class AssignmentUpdateView(TeacherOnlyMixin,
                           AssignmentCreateUpdateMixin,
                           generic.UpdateView):
    pass


class AssignmentDeleteView(TeacherOnlyMixin,
                           ProtectedFormMixin,
                           generic.DeleteView):
    model = Assignment
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return reverse('assignment_list_teacher')

    def is_form_allowed(self, user, obj):
        return user in obj.course_offering.teachers.all()


class MarksSheetMixin(object):
    model = AssignmentStudent
    template_name = "learning/marks_sheet.html"
    context_object_name = 'assignment_list'

    def get_queryset(self):
        return (super(MarksSheetMixin, self).get_queryset()
                .order_by('assignment__course_offering',
                          'student',
                          'assignment')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))

    def get_context_data(self, *args, **kwargs):
        context = (super(MarksSheetMixin, self)
                   .get_context_data(*args, **kwargs))
        data = context[self.context_object_name]
        # implying that the data is already sorted
        structured = OrderedDict()
        for a_s in data:
            offering = a_s.assignment.course_offering
            if offering not in structured:
                structured[offering] = OrderedDict()
            if a_s.student not in structured[offering]:
                structured[offering][a_s.student] = OrderedDict()
            structured[offering][a_s.student][a_s.assignment] = a_s
        headers = OrderedDict()
        for offering, by_student in structured.items():
            header = by_student.values()[0].keys()
            headers[offering] = header
            for _, by_assignment in by_student.items():
                # we should check for "assignment consistency": that all
                # assignments are similar for all students in particular
                # course offering
                assert by_assignment.keys() == header
        # this is a hack for passing headers "indexed" by offering
        context['structured'] = [(offering, headers[offering], by_student)
                                 for offering, by_student
                                 in structured.items()]
        context['user_type'] = self.user_type
        return context


class MarksSheetTeacherView(TeacherOnlyMixin,
                            MarksSheetMixin,
                            generic.ListView):
    user_type = 'teacher'

    def get_queryset(self):
        return (super(MarksSheetTeacherView, self).get_queryset()
                .filter(assignment__course_offering__teachers=
                        self.request.user))


class MarksSheetStaffView(StaffOnlyMixin,
                          MarksSheetMixin,
                          generic.ListView):
    user_type = 'staff'
