# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import csv
import datetime
import logging
import os
from calendar import Calendar
from collections import OrderedDict, defaultdict
from itertools import chain

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, \
    MultipleObjectsReturned

from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q, F
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta

from core.views import StudentOnlyMixin, TeacherOnlyMixin, StaffOnlyMixin, \
    ProtectedFormMixin, LoginRequiredMixin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews, Enrollment, Assignment, AssignmentStudent, AssignmentComment, \
    CourseClassAttachment, AssignmentNotification, \
    CourseOfferingNewsNotification, Semester, NonCourseEvent
from learning.forms import CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm, \
    CourseClassForm, CourseForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm, \
    MarksSheetTeacherFormFabrique
from core.notifications import get_unread_notifications_cache
from . import utils


logger = logging.getLogger(__name__)


class TimetableTeacherView(TeacherOnlyMixin,
                           generic.ListView):
    model = CourseClass
    user_type = 'teacher'
    template_name = "learning/timetable_teacher.html"

    def __init__(self, *args, **kwargs):
        self._context_weeks = None
        super(TimetableTeacherView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        month_qstr = self.request.GET.get('month')
        year_qstr = self.request.GET.get('year')
        try:
            year = int(year_qstr)
            month = int(month_qstr)
        except TypeError:
            today = now().date()
            year, month = today.year, today.month
        chosen_month_date = datetime.date(year=year, month=month, day=1)
        prev_month_date = chosen_month_date + relativedelta(months=-1)
        next_month_date = chosen_month_date + relativedelta(months=+1)
        self._context_dates = {'month': month,
                               'year': year,
                               'current_date': chosen_month_date,
                               'prev_date': prev_month_date,
                               'next_date': next_month_date}
        return (CourseClass.objects
                .filter(date__month=month,
                        date__year=year,
                        course_offering__teachers=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableTeacherView, self)
                   .get_context_data(*args, **kwargs))
        context.update(self._context_dates)
        context['user_type'] = self.user_type
        return context


class TimetableStudentView(StudentOnlyMixin,
                           generic.ListView):
    model = CourseClass
    user_type = 'student'
    template_name = "learning/timetable_student.html"

    def __init__(self, *args, **kwargs):
        self._context_weeks = None
        super(TimetableStudentView, self).__init__(*args, **kwargs)

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
                .filter(date__range=[start, end],
                        course_offering__enrolled_students=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableStudentView, self)
                   .get_context_data(*args, **kwargs))
        context.update(self._context_weeks)
        context['user_type'] = self.user_type
        return context


class CalendarMixin(object):
    model = CourseClass
    template_name = "learning/calendar.html"

    def __init__(self, *args, **kwargs):
        self._month_date = None
        self._non_course_events = None
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

        # FIXME(Dmitry): somewhat dirty, come up with better generalization
        self._non_course_events \
            = (NonCourseEvent.objects
               .filter(Q(date__month=month,
                         date__year=year)
                       | Q(date__month=prev_month_date.month,
                           date__year=prev_month_date.year)
                       | Q(date__month=next_month_date.month,
                           date__year=next_month_date.year))
               .order_by('date', 'starts_at')
               .select_related('venue'))

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

    def get_context_data(self, *args, **kwargs):
        context = (super(CalendarMixin, self)
                   .get_context_data(*args, **kwargs))
        context['next_date'] = self._month_date + relativedelta(months=1)
        context['prev_date'] = self._month_date + relativedelta(months=-1)
        context['user_type'] = self.user_type

        events = sorted(chain(context['object_list'],
                              self._non_course_events.all()),
                        key=lambda evt: (evt.date, evt.starts_at))

        dates_to_events = defaultdict(list)
        for event in events:
            dates_to_events[event.date].append(event)

        cal = Calendar(0)

        month_cal = cal.monthdatescalendar(self._month_date.year,
                                           self._month_date.month)
        month = [(week[0].isocalendar()[1],
                  [(day, dates_to_events[day],
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


class CalendarStudentView(StudentOnlyMixin,
                          CalendarMixin,
                          generic.ListView):
    user_type = "student"

    def get_queryset(self):
        return (super(CalendarStudentView, self).get_queryset()
                .filter(course_offering__enrolled_students=self.request.user))


class CalendarFullView(LoginRequiredMixin,
                       CalendarMixin,
                       generic.ListView):
    user_type = 'full'


class SemesterListView(generic.ListView):
    model = Semester
    template_name = "learning/semester_list.html"

    def get_queryset(self):
        return (self.model.objects
                .prefetch_related("courseoffering_set",
                                  "courseoffering_set__course",
                                  "courseoffering_set__teachers"))

    def get_context_data(self, **kwargs):
        context = (super(SemesterListView, self)
                   .get_context_data(**kwargs))
        semester_list = list(context["semester_list"])
        if not semester_list:
            return context

        for semester in semester_list:
            # HACK(lebedev): since we don't have a 'Prefetch' object
            # yet, there's no way to impose ordering on the related
            # table.
            semester.courseofferings = sorted(
                semester.courseoffering_set.all(),
                key=lambda co: co.course.name)

        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)

        context["semester_list"] = [
            (a, s) for s, a in utils.grouper(semester_list, 2)
        ]
        return context


class CourseListMixin(object):
    model = CourseOffering
    template_name = "learning/courses_list.html"
    context_object_name = 'course_list'

    list_type = 'all'

    def get_queryset(self):
        return (self.model.objects
                .order_by('-semester__year', '-semester__type', 'course__name')
                .select_related('course', 'semester')
                .prefetch_related('teachers'))

    def get_context_data(self, **kwargs):
        context = (super(CourseListMixin, self)
                   .get_context_data(**kwargs))
        ongoing, archive = utils.split_list(context['course_list'],
                                            lambda course: course.is_ongoing)
        context['course_list_ongoing'] = ongoing
        context['course_list_archive'] = archive
        context['list_type'] = self.list_type
        return context


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

    def get_context_data(self, **kwargs):
        context = (super(CourseStudentListView, self)
                   .get_context_data(**kwargs))
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

    def get_context_data(self, **kwargs):
        context = (super(CourseDetailView, self)
                   .get_context_data(**kwargs))
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class CourseUpdateView(StaffOnlyMixin,
                       ProtectedFormMixin,
                       generic.UpdateView):
    model = Course
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_superuser


class GetCourseOfferingObjectMixin(object):
    model = CourseOffering

    def get_object(self):
        try:
            year, semester_type = self.kwargs['semester_slug'].split("-", 1)
            year = int(year)
        except ValueError:
            raise Http404

        return get_object_or_404(
            self.model.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug'])
            .select_related('course',
                            'semester')
            .prefetch_related('teachers',
                              'courseclass_set',
                              'courseclass_set__venue',
                              'courseofferingnews_set',
                              'assignment_set'))


class CourseOfferingDetailView(GetCourseOfferingObjectMixin,
                               generic.DetailView):
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingDetailView, self)
                   .get_context_data(*args, **kwargs))
        is_enrolled = (self.request.user.is_authenticated() and
                       self.request.user.is_student and
                       (self.request.user
                        .enrolled_on_set
                        .filter(pk=self.object.pk)
                        .exists()))
        context['is_enrolled'] = is_enrolled
        is_actual_teacher = (self.request.user.is_authenticated() and
                             self.request.user in self.object.teachers.all())
        context['is_actual_teacher'] = is_actual_teacher
        assignments = self.object.assignment_set.all().order_by('created')
        for assignment in assignments:
            if is_actual_teacher or self.request.user.is_superuser:
                setattr(assignment, 'magic_link',
                        reverse("assignment_detail_teacher",
                                args=[assignment.pk]))
            elif is_enrolled:
                try:
                    a_s = (AssignmentStudent.objects
                           .filter(assignment=assignment,
                                   student=self.request.user)
                           .get())
                    setattr(assignment, 'magic_link',
                            reverse("a_s_detail_student", args=[a_s.pk]))
                except ObjectDoesNotExist:
                    logger.error("can't find AssignmentStudent for "
                                 "student ID {0}, assignment ID {1}"
                                 .format(self.request.user.pk, assignment.pk))
        context['assignments'] = assignments

        # Not sure if it's the best place for this, but it's the simplest one
        if self.request.user.is_authenticated():
            cache = get_unread_notifications_cache()
            if self.object in cache.courseoffering_news:
                (CourseOfferingNewsNotification.unread
                 .filter(course_offering_news__course_offering=self.object,
                         user=self.request.user)
                 .update(is_unread=False))

        return context


class CourseOfferingEditDescrView(TeacherOnlyMixin,
                                  ProtectedFormMixin,
                                  GetCourseOfferingObjectMixin,
                                  generic.UpdateView):
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingEditDescrForm

    def is_form_allowed(self, user, obj):
        return user.is_superuser or \
            (user in obj.teachers.all())


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
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.save()
        return redirect(self.get_success_url())

    def is_form_allowed(self, user, obj):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        self._course_offering = get_object_or_404(
            CourseOffering.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug']))
        return user.is_superuser or \
            (user in self._course_offering.teachers.all())


class CourseOfferingNewsUpdateView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user.is_superuser or \
            (user in obj.course_offering.teachers.all())


class CourseOfferingNewsDeleteView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user.is_superuser or \
            (user in obj.course_offering.teachers.all())


class CourseOfferingEnrollView(StudentOnlyMixin, generic.FormView):
    http_method_names = ['post']
    form_class = CourseOfferingPKForm

    def form_valid(self, form):
        course_offering = get_object_or_404(
            CourseOffering.objects.filter(
                pk=form.cleaned_data['course_offering_pk']))
        Enrollment.objects.get_or_create(
            student=self.request.user, course_offering=course_offering)
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


class CourseClassCreateUpdateMixin(ProtectedFormMixin):
    model = CourseClass
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseClassForm

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseClassCreateUpdateMixin, self).__init__(*args, **kwargs)

    def is_form_allowed(self, user, obj):
        return (obj is None or
                user.is_superuser or
                user in obj.course_offering.teachers.all())

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
        if self.object is not None:
            # NOTE(Dmitry): dirty, but I don't see a better way given
            #               that forms are generated in code
            remove_links = "<ul class=\"list-unstyled\">{0}</ul>".format(
                "".join("<li>"
                        "<i class=\"fa fa-times\"></i>&nbsp;"
                        "<a href=\"{0}\">{1}</a>"
                        "</li>"
                        .format(reverse('course_class_attachment_delete',
                                        args=(self.object.pk,
                                              attachment.pk)),
                                attachment.material_file_name)
                        for attachment
                        in self.object.courseclassattachment_set.all()))
        else:
            remove_links = ""
        return form_class(self.request.user,
                          remove_links=remove_links,
                          **self.get_form_kwargs())

    def form_valid(self, form):
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            self.object = form.save()
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()
        else:
            self.object = form.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.GET.get('back') == 'timetable':
            return reverse('timetable_teacher')
        if self.request.GET.get('back') == 'course_offering':
            return self._course_offering.get_absolute_url()
        if self.request.GET.get('back') == 'calendar':
            return reverse('calendar_teacher')
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


class CourseClassAttachmentDeleteView(TeacherOnlyMixin,
                                      ProtectedFormMixin,
                                      generic.DeleteView):
    model = CourseClassAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return user.is_superuser or \
            (user in obj.course_class.course_offering.teachers.all())

    def get_success_url(self):
        return reverse('course_class_edit', args=[self.object.course_class.pk])

    def delete(self, request, *args, **kwargs):
        resp = (super(CourseClassAttachmentDeleteView, self)
                .delete(request, *args, **kwargs))
        os.remove(self.object.material.path)
        return resp


class CourseClassDeleteView(TeacherOnlyMixin,
                            ProtectedFormMixin,
                            generic.DeleteView):
    model = CourseClass
    template_name = "learning/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')

    def is_form_allowed(self, user, obj):
        return user.is_superuser or \
            (user in obj.course_offering.teachers.all())


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
                # FIXME: this prefetch doesn't seem to work
                .prefetch_related('assignmentnotification_set')
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
        base_qs = \
            (self.model.objects
             .filter(assignment__course_offering__teachers=self.request.user,
                     grade__isnull=True)
             .order_by('-assignment__deadline_at',
                       'assignment__course_offering__course__name',
                       'assignment__pk',
                       'student__last_name')
             .select_related('assignment',
                             'assignment__course_offering',
                             'assignment__course_offering__course',
                             'assignment__course_offering__semester',
                             'student'))
        if self.request.GET.get('show_all') == 'true':
            return base_qs
        else:
            return base_qs.filter(assignment__is_online=True,
                                  grade__isnull=True)

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherListView, self)
                   .get_context_data(*args, **kwargs))
        if self.request.GET.get('show_all') == 'true':
            open_ = context['assignment_list']
        else:
            a_s_pks = [a_s.pk for a_s in context['assignment_list']]
            passed_set = set((AssignmentComment.objects
                              .filter(assignment_student__in=a_s_pks,
                                      author=F('assignment_student__student'))
                              .values_list('assignment_student__pk',
                                           flat=True)))
            open_ = [a_s
                     for a_s in context['assignment_list']
                     if a_s.pk in passed_set]
        archive = (Assignment.objects
                   .filter(course_offering__teachers=self.request.user)
                   .order_by('-deadline_at',
                             'course_offering__course__name',
                             'pk')
                   .select_related('course_offering',
                                   'course_offering__course',
                                   'course_offering__semester'))
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['user_type'] = self.user_type
        context['show_all'] = \
            (self.request.GET.get('show_all') == 'true')
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

        is_actual_teacher = (
            self.request.user in (self.object
                                  .course_offering
                                  .teachers.all()))
        if not is_actual_teacher and not self.request.user.is_superuser:
            raise PermissionDenied
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

        # Not sure if it's the best place for this, but it's the simplest one
        (AssignmentNotification.unread
         .filter(assignment_student=a_s,
                 user=self.request.user)
         .update(is_unread=False))

        # This should guard against reading other's assignments. Not generic
        # enough, but can't think of better way
        if (not self.request.user.is_superuser
            and (self.user_type == 'student'
                 and not a_s.student == self.request.user)):
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
        else:
            url = reverse('a_s_detail_teacher', args=[a_s.pk])
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
        co = a_s.assignment.course_offering
        initial = {'grade': a_s.grade}
        is_actual_teacher = (
            self.request.user in (a_s
                                  .assignment
                                  .course_offering
                                  .teachers.all()))
        if not is_actual_teacher and not self.request.user.is_superuser:
            raise PermissionDenied
        context['is_actual_teacher'] = is_actual_teacher
        context['grade_form'] = AssignmentGradeForm(
            initial, grade_max=a_s.assignment.grade_max)
        base = (
            AssignmentStudent.objects
            .filter(grade__isnull=True,
                    is_passed=True,
                    assignment__course_offering=co,
                    assignment__course_offering__teachers=self.request.user)
            .order_by('assignment__deadline_at',
                      'assignment__course_offering__course__name',
                      'pk'))
        next_a_s = (base.filter(pk__gt=a_s.pk).first() or
                    base.filter(pk__lt=a_s.pk).first())
        context['next_a_s_pk'] = next_a_s.pk if next_a_s else None
        return context

    def post(self, request, *args, **kwargs):
        if 'grading_form' in request.POST:
            pk = self.kwargs.get('pk')
            a_s = get_object_or_404(AssignmentStudent.objects.filter(pk=pk))
            form = AssignmentGradeForm(request.POST,
                                       grade_max=a_s.assignment.grade_max)

            # Too hard to use ProtectedFormMixin here, let's just inline it's
            # logic. A little drawback is that teachers still can leave
            # comments under other's teachers assignments, but can not grade,
            # so it's acceptable, IMO.
            teachers = a_s.assignment.course_offering.teachers.all()
            if request.user not in teachers:
                raise PermissionDenied

            if form.is_valid():
                a_s.grade = form.cleaned_data['grade']
                a_s.save()
                return redirect(reverse('a_s_detail_teacher', args=[pk]))
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(form.errors))
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


# No ProtectedFormMixin here because we are filtering out other's courses
# on form level (see __init__ of AssignmentForm)
class AssignmentCreateView(TeacherOnlyMixin,
                           AssignmentCreateUpdateMixin,
                           generic.CreateView):
    def get_initial(self):
        initial = super(AssignmentCreateView, self).get_initial()
        try:
            course_offering = (CourseOffering.objects
                               .get(pk=self.request.GET.get('co')))
            initial.update({'course_offering': course_offering})
        except ObjectDoesNotExist:
            pass
        return initial


# Same here
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
        return user.is_superuser or \
            (user in obj.course_offering.teachers.all())


class MarksSheetTeacherDispatchView(TeacherOnlyMixin,
                                    generic.ListView):
    class RedirectException(Exception):
        def __init__(self, url):
            self.url = url

    is_for_staff = None
    ms_url_name = None
    model = Semester
    template_name = "learning/markssheet_teacher_dispatch.html"

    def __init__(self, *args, **kwargs):
        super(MarksSheetTeacherDispatchView, self).__init__(*args, **kwargs)
        if kwargs.get('is_for_staff'):
            self.is_for_staff = True
            self.ms_url_name = 'course_markssheet_staff'
        else:
            self.is_for_staff = False
            self.ms_url_name = 'markssheet_teacher'

    def get(self, request, *args, **kwargs):
        try:
            return (super(MarksSheetTeacherDispatchView, self)
                    .get(request, *args, **kwargs))
        except MarksSheetTeacherDispatchView.RedirectException as re:
            return HttpResponseRedirect(re.url)

    def get_queryset(self):
        return (self.model.objects
                .prefetch_related("courseoffering_set",
                                  "courseoffering_set__course"))

    def get_context_data(self, *args, **kwargs):
        context = (super(MarksSheetTeacherDispatchView, self)
                   .get_context_data(**kwargs))
        semester_list = list(context["semester_list"])
        if not semester_list:
            return context

        now_ = now()
        for semester in semester_list:
            if self.request.user.is_superuser:
                cos = semester.courseoffering_set.all()
            else:
                cos = (semester.courseoffering_set
                       .filter(teachers=self.request.user))
            semester.courseofferings = sorted(
                cos,
                key=lambda co: co.course.name)
            if len(semester.courseofferings) == 1 \
               and semester.starts_at <= now_ <= semester.ends_at:
                co = semester.courseofferings[0]
                url = reverse(self.ms_url_name,
                              args=[co.course.slug,
                                    co.semester.year,
                                    co.semester.type])
                raise MarksSheetTeacherDispatchView.RedirectException(url)

        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)

        context["semester_list"] = [
            (a, s) for s, a in utils.grouper(semester_list, 2)]
        context['ms_url_name'] = self.ms_url_name
        return context



class MarksSheetTeacherView(TeacherOnlyMixin,
                            generic.FormView):
    user_type = 'teacher'
    template_name = "learning/markssheet_teacher.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        self.a_s_list = None
        self.enrollment_list = None
        self.course_offering_list = None
        self.course_offering = None
        super(MarksSheetTeacherView, self).__init__(*args, **kwargs)

    def get_form_class(self):
        try:
            semester_year = int(self.kwargs['semester_year'])
        except ValueError, TypeError:
            raise Http404('Course offering not found')
        if self.request.user.is_superuser:
            base_qs = CourseOffering.objects
        else:
            base_qs = (CourseOffering.objects
                       .filter(teachers=self.request.user))
        try:
            co = (base_qs
                  .select_related('semester', 'course')
                  .get(course__slug=self.kwargs['course_slug'],
                       semester__type=self.kwargs['semester_type'],
                       semester__year=semester_year))
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        a_s_list = (AssignmentStudent.objects
                    .filter(assignment__course_offering=co)
                    .order_by('assignment__course_offering',
                              'student',
                              'assignment')
                    .select_related('assignment',
                                    'assignment__course_offering',
                                    'assignment__course_offering__course',
                                    'assignment__course_offering__semester',
                                    'student'))
        enrollment_list = (Enrollment.objects
                           .filter(course_offering=co)
                           .order_by('course_offering__semester__year',
                                     'course_offering__semester__type',
                                     'course_offering',
                                     'student__last_name',
                                     'student__first_name')
                           .select_related('course_offering', 'student'))
        course_offering_list = (CourseOffering.objects
                                .filter(teachers=self.request.user)
                                .order_by('-semester__year',
                                          '-semester__type',
                                          '-pk')
                                .select_related('semester', 'course'))
        self.a_s_list = a_s_list
        self.enrollment_list = enrollment_list
        self.course_offering = co
        self.course_offering_list = course_offering_list
        return (MarksSheetTeacherFormFabrique
                .build_form_class(a_s_list,
                                  enrollment_list))

    def get_initial(self):
        return (MarksSheetTeacherFormFabrique
                .transform_to_initial(self.a_s_list, self.enrollment_list))

    def get_success_url(self):
        co = self.course_offering
        return reverse('markssheet_teacher', args=[co.course.slug,
                                                   co.semester.year,
                                                   co.semester.type])

    def form_valid(self, form):
        a_s_index, enrollment_index = \
            MarksSheetTeacherFormFabrique.build_indexes(self.a_s_list,
                                                        self.enrollment_list)
        for field in form.changed_data:
            if field in a_s_index:
                a_s = a_s_index[field]
                a_s.grade = form.cleaned_data[field]
                a_s.save()
                continue
            elif field in enrollment_index:
                enrollment = enrollment_index[field]
                enrollment.grade = form.cleaned_data[field]
                enrollment.save()
                continue
        return redirect(self.get_success_url())

    def get_context_data(self, *args, **kwargs):
        def get_a_s_field(a_s_pk):
            return kwargs['form']['a_s_{0}'.format(a_s_pk)]

        def get_final_grade_field(course_offering_pk, student_pk):
            key = 'final_grade_{0}_{1}'.format(course_offering_pk, student_pk)
            return kwargs['form'][key]

        context = (super(MarksSheetTeacherView, self)
                   .get_context_data(*args, **kwargs))
        data = self.a_s_list
        # implying that the data is already sorted
        structured = OrderedDict()
        for enrollment in self.enrollment_list:
            student = enrollment.student
            if student not in structured:
                structured[student] = OrderedDict()
        for a_s in data:
            # if assignment is "offline", provide ModelForm instead of
            # the object itself
            if a_s.assignment.is_online:
                cell = a_s
            else:
                cell = get_a_s_field(a_s.pk)
            structured[a_s.student][a_s.assignment] = cell

        if len(structured) > 0:
            header = structured.values()[0].keys()
        else:
            header = []
        for _, by_assignment in structured.items():
            # we should check for "assignment consistency": that all
            # assignments are similar for all students in particular
            # course offering
            assert by_assignment.keys() == header

        context['course_offering'] = self.course_offering
        context['course_offering_list'] = self.course_offering_list
        context['header'] = header
        context['structured'] = [(student,
                                  get_final_grade_field(self.course_offering.pk,
                                                        student.pk),
                                  by_assignment)
                                 for student, by_assignment
                                 in structured.iteritems()]
        context['user_type'] = self.user_type
        return context


class MarksSheetTeacherCSVView(TeacherOnlyMixin,
                               generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        course_slug = kwargs['course_slug']
        semester_slug = kwargs['semester_slug']
        try:
            semester_year, semester_type = semester_slug.split('-')
            semester_year = int(semester_year)
        except ValueError, TypeError:
            raise Http404('Course offering not found')
        if request.user.is_superuser:
            base_qs = CourseOffering.objects
        else:
            base_qs = CourseOffering.objects.filter(teachers=request.user)
        try:
            co = base_qs.get(
                course__slug=course_slug,
                semester__type=semester_type,
                semester__year=semester_year)
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        a_ss = (AssignmentStudent.objects
                .filter(assignment__course_offering=co)
                .order_by('student', 'assignment')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))
        enrollments = (Enrollment.objects
                       .filter(course_offering=co)
                       .select_related('course_offering', 'student'))
        structured = OrderedDict()
        enrollment_grades = {}
        for enrollment in enrollments:
            student = enrollment.student
            enrollment_grades[student] = enrollment.grade_display
            if student not in structured:
                structured[student] = OrderedDict()
        for a_s in a_ss:
            structured[a_s.student][a_s.assignment] = a_s.grade

        header = structured.values()[0].keys()
        for _, by_assignment in structured.items():
            # we should check for "assignment consistency": that all
            # assignments are similar for all students in particular
            # course offering
            assert by_assignment.keys() == header

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename \
            = "{}-{}.csv".format(kwargs['course_slug'],
                                 kwargs['semester_slug'])
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(['Фамилия'.encode('utf8'),
                         'Имя'.encode('utf8')]
                        + [smart_text(a.title).encode('utf8')
                           for a in header]
                        + ['Итоговая оценка'.encode('utf8')])
        for student, by_assignment in structured.items():
            writer.writerow([(smart_text(x if x is not None else '')
                              .encode('utf8'))
                             for x in
                             ([student.last_name, student.first_name]
                              + by_assignment.values()
                              + [enrollment_grades[student]])])
        return response


class MarksSheetStaffView(StaffOnlyMixin,
                          generic.TemplateView):
    user_type = 'staff'
    success_url = 'markssheet_staff'
    template_name = "learning/markssheet_staff.html"
    context_object_name = 'assignment_list'

    def get_context_data(self, *args, **kwargs):
        enrollment_index = {(enrollment.student.pk,
                             enrollment.course_offering.pk):
                            enrollment
                            for enrollment in
                            (Enrollment.objects
                             .select_related('course_offering', 'student'))}
        offerings_list = (CourseOffering.objects
                          .select_related('course')
                          .order_by('course__name'))

        students_list = (get_user_model().objects
                         .filter(groups__name='Student')
                         .select_related('student',
                                         'overall_grade'))
        enrollment_years = sorted(set(x.enrollment_year
                                      for x in students_list
                                      if x.enrollment_year is not None))
        try:
            year = int(self.request.GET.get('enrollment_year'))
        except (TypeError, ValueError):
            year = None

        if year is not None:
            students_list = filter(lambda s: s.enrollment_year == year,
                                   students_list)
        else:
            students_list = students_list

        def merge_cells(cell1, cell2):
            grade_priorities = \
                {Enrollment.SHORT_GRADES['not_graded']: 0,
                 Enrollment.SHORT_GRADES['unsatisfactory']: 1,
                 Enrollment.SHORT_GRADES['pass']: 2,
                 Enrollment.SHORT_GRADES['good']: 3,
                 Enrollment.SHORT_GRADES['excellent']: 4}
            if not cell1:
                return cell2
            if not cell2:
                return cell1
            return {'grade': (cell1['grade']
                              if (grade_priorities[cell1['grade']] >
                                  grade_priorities[cell2['grade']])
                              else cell2['grade']),
                    'enrolled': (cell1['enrolled'] or
                                 cell2['enrolled'])}

        context = (super(MarksSheetStaffView, self)
                   .get_context_data(*args, **kwargs))

        # implying that the data is already sorted
        structured = OrderedDict()
        for student in students_list:
            structured[student] = OrderedDict()
            for offering in offerings_list:
                maybe_existing_cell = structured[student].get(offering.course)
                idx = (student.pk, offering.pk)
                maybe_enrollment = enrollment_index.get(idx)
                if maybe_enrollment:
                    cell = {'grade': maybe_enrollment.grade_short,
                            'enrolled': True}
                else:
                    cell = {'grade': Enrollment.SHORT_GRADES['not_graded'],
                            'enrolled': False}
                structured[student][offering.course] = \
                    merge_cells(maybe_existing_cell, cell)

        if structured.values():
            header = structured.values()[0].keys()
            for by_offering in structured.values():
                # we should check for "assignment consistency": that all
                # assignments are similar for all students in particular
                # course offering
                assert by_offering.keys() == header
        else:
            header = []

        context['structured'] = [(student, by_course)
                                 for student, by_course
                                 in structured.iteritems()]
        context['header'] = header
        context['user_type'] = self.user_type
        context['enrollment_years'] = enrollment_years
        context['current_year'] = year
        return context


class NonCourseEventDetailView(generic.DetailView):
    model = NonCourseEvent
    context_object_name = 'event'
    template_name = "learning/noncourseevent_detail.html"
