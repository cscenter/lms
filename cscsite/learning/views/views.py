import re
import datetime
import itertools
import logging
import os
import posixpath
from collections import OrderedDict
from urllib.parse import urlencode

import nbconvert
import unicodecsv as csv
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, \
    ValidationError
from django.db.models import Q, Prefetch, When, Value, Case
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseRedirect, HttpResponseForbidden
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.edit import BaseUpdateView
from six import viewvalues
from vanilla import CreateView, UpdateView, DeleteView

from core import comment_persistence
from core.exceptions import Redirect
from core.utils import hashids, render_markdown, is_club_site
from core.views import ProtectedFormMixin, LoginRequiredMixin
from learning import utils
from learning.calendar import CalendarQueryParams
from learning.forms import CourseClassForm, CourseForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm, \
    MarksSheetTeacherImportGradesForm, GradeBookFormFactory, \
    AssignmentModalCommentForm
from learning.management.imports import ImportGradesByStepicID, \
    ImportGradesByYandexLogin
from learning.models import Course, CourseClass, CourseOffering, Venue, \
    Enrollment, Assignment, AssignmentAttachment, \
    StudentAssignment, AssignmentComment, \
    CourseClassAttachment, AssignmentNotification, \
    Semester, NonCourseEvent, \
    OnlineCourse, InternationalSchool
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT, \
    ASSIGNMENT_TASK_ATTACHMENT, SEMESTER_AUTUMN_SPRING_INDEX_OFFSET, \
    FOUNDATION_YEAR, SEMESTER_TYPES, GRADES, \
    GRADING_TYPES
from learning.utils import get_current_semester_pair, get_term_index, now_local
from learning.viewmixins import TeacherOnlyMixin, StudentOnlyMixin, \
    CuratorOnlyMixin
from learning.views.generic import CalendarGenericView
from learning.views.utils import get_student_city_code, get_teacher_city_code, \
    get_co_from_query_params

logger = logging.getLogger(__name__)

DROP_ATTACHMENT_LINK = """
<a href="{0}"><i class="fa fa-trash-o"></i>&nbsp;{1}</a>"""


class TimetableTeacherView(TeacherOnlyMixin, generic.TemplateView):
    user_type = 'teacher'
    template_name = "learning/timetable_teacher.html"

    def get(self, request, *args, **kwargs):
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        # FIXME: get teacher city code????
        city_code = request.city_code
        today = now_local(city_code)
        year = query_params.validated_data.get('year', today.year)
        month = query_params.validated_data.get('month', today.month)
        context = self.get_context_data(year, month, **kwargs)
        return self.render_to_response(context)

    def get_queryset(self, year, month):
        return (CourseClass.objects
                .filter(date__month=month,
                        date__year=year,
                        course_offering__teachers=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, year, month, **kwargs):
        chosen_month_date = datetime.date(year=year, month=month, day=1)
        prev_month_date = chosen_month_date + relativedelta(months=-1)
        next_month_date = chosen_month_date + relativedelta(months=+1)
        context = {
            'object_list': self.get_queryset(year, month),
            'month': month,
            'year': year,
            'current_date': chosen_month_date,
            'prev_date': prev_month_date,
            'next_date': next_month_date,
            'user_type': self.user_type
        }
        return context


class TimetableStudentView(StudentOnlyMixin, generic.TemplateView):
    model = CourseClass
    user_type = 'student'
    template_name = "learning/timetable_student.html"

    def get(self, request, *args, **kwargs):
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        # FIXME: get teacher city code????
        city_code = request.city_code
        today = now_local(city_code)
        # This returns current week number. Beware: the week's number
        # is as of ISO8601, so 29th of December can be reported as
        # 1st week of the next year.
        today_year, today_week, _ = today.isocalendar()
        year = query_params.validated_data.get('year', today_year)
        week = query_params.validated_data.get('week', today_week)
        context = self.get_context_data(year, week, **kwargs)
        return self.render_to_response(context)

    def get_queryset(self, start, end):
        return (CourseClass.objects
                .filter(date__range=[start, end],
                        course_offering__enrollment__student_id=self.request.user.pk,
                        course_offering__enrollment__is_deleted=False)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, year, week, **kwargs):
        start = utils.iso_to_gregorian(year, week, 1)
        end = utils.iso_to_gregorian(year, week, 7)
        next_year, next_week, _ = (start +
                                   datetime.timedelta(weeks=1)).isocalendar()
        prev_year, prev_week, _ = (start +
                                   datetime.timedelta(weeks=-1)).isocalendar()
        context = {
            'object_list': self.get_queryset(start, end),
            'user_type': self.user_type,
            'week': week,
            'week_start': start,
            'week_end': end,
            'month': start.month,
            'year': year,
            'prev_year': prev_year,
            'prev_week': prev_week,
            'next_year': next_year,
            'next_week': next_week,
        }
        return context


class CalendarStudentFullView(StudentOnlyMixin, CalendarGenericView):
    """
    Shows all non-course events and all classes to authenticated student.
    """
    def get_city_code(self):
        try:
            return get_student_city_code(self.request)
        except ValueError as e:
            messages.error(self.request, e.args[0])
            raise Redirect('/')

    def get_events(self, year, month, city_code):
        return [self._get_classes(year, month, city_code),
                self._get_non_course_events(year, month, city_code)]

    @staticmethod
    def _get_non_course_events(year, month, city_code):
        return (NonCourseEvent.objects
                .for_calendar()
                .for_city(city_code)
                .in_month(year, month))

    def _get_classes(self, year, month, city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .for_city(city_code))


class CalendarStudentView(CalendarStudentFullView):
    """
    Shows all non-course events and classes for courses on which authenticated
    student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def _get_classes(self, year, month, city_code):
        qs = super()._get_classes(year, month, city_code)
        return qs.for_student(self.request.user)


class CalendarTeacherFullView(TeacherOnlyMixin, CalendarGenericView):
    """Shows all non-course events and all classes to authenticated teacher."""

    def get_city_code(self):
        return get_teacher_city_code(self.request)

    def get_events(self, year, month, city_code):
        return [self._get_classes(year, month, city_code),
                self._get_non_course_events(year, month, city_code)]

    # FIXME: What about non-course events? What cities to show??? Both?
    @staticmethod
    def _get_non_course_events(year, month, city_code):
        return (NonCourseEvent.objects
                .for_calendar()
                .for_city(city_code)
                .in_month(year, month))

    # FIXME: What about non-course events? What cities to show??? Both??????
    def _get_classes(self, year, month, city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .for_city(city_code))


class CalendarTeacherView(CalendarTeacherFullView):
    """
    Shows all non-course events and classes for courses in which authenticated
    teacher participated.
    """
    calendar_type = 'teacher'
    template_name = "learning/calendar.html"

    def _get_classes(self, year, month, city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .for_teacher(self.request.user))


class CoursesListView(generic.ListView):
    model = Semester
    template_name = "learning/courses/list.html"

    def get_queryset(self):
        co_queryset = (CourseOffering.objects
                       .in_city(self.request.city_code)
                       .open_only(is_club_site())
                       .select_related('course')
                       .prefetch_related('teachers')
                       .order_by('course__name'))
        q = (Semester.objects
            .prefetch_related(
                Prefetch('courseoffering_set',
                         queryset=co_queryset,
                         to_attr='courseofferings')))
        # Courses in CS Center started at 2011 year
        if not is_club_site():
            q = (q.filter(year__gte=2011)
                .exclude(type=Case(
                    When(year=2011, then=Value(Semester.TYPES.spring)),
                    default=Value(""))))
        return q

    def get_context_data(self, **kwargs):
        context = super(CoursesListView, self).get_context_data(**kwargs)
        semester_list = [s for s in context["semester_list"]
                         if s.type != Semester.TYPES.summer]
        if not semester_list:
            context["semester_list"] = semester_list
            return context
        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)
        # Hide empty pairs
        context["semester_list"] = [
            (a, s) for s, a in utils.grouper(semester_list, 2) if \
            (a and a.courseofferings) or (s and s.courseofferings)
            ]

        return context


class CourseTeacherListView(TeacherOnlyMixin,
                            generic.ListView):
    model = CourseOffering
    context_object_name = 'course_list'
    template_name = "learning/courses/teaching_list.html"

    def get_queryset(self):
        return (self.model.objects
                .filter(teachers=self.request.user)
                .select_related('course', 'semester')
                .prefetch_related('teachers')
                .order_by('-semester__year', '-semester__type', 'course__name'))


class CourseStudentListView(StudentOnlyMixin,
                            generic.TemplateView):
    model = CourseOffering
    context_object_name = 'course_list'
    template_name = "learning/courses/learning_my_courses.html"

    def get_context_data(self, **kwargs):
        current_year, current_term = get_current_semester_pair()
        # Get all student enrollments and split them
        # FIXME: Наверное, я хочу сразу получить все COurseOffering!
        # Сначала id всех активных записей юзера, а там уже CourseOffering! Это будет легче в плане запросов.
        enrolled_on = (Enrollment.active.site_related(self.request)
                       .filter(student=self.request.user)
                       .order_by('course_offering__semester__year',
                                 '-course_offering__semester__type',
                                 'course_offering__course__name')
                       .select_related('course_offering',
                                       'course_offering__course',
                                       'course_offering__semester')
                       .prefetch_related('course_offering__teachers'))
        # FIXME: remove split_list
        enrolled_ongoing, enrolled_archive = utils.split_list(
            enrolled_on,
            lambda e: (e.course_offering.semester.year == current_year
                       and e.course_offering.semester.type == current_term))

        current_term_index = get_term_index(current_year, current_term)
        available = (CourseOffering.objects
                     .in_city(self.request.city_code)
                     .open_only(is_club_site())
                     .filter(semester__index=current_term_index)
                     .select_related('course', 'semester')
                     .order_by('semester__year', '-semester__type',
                               'course__name')
                     .prefetch_related('teachers'))
        # Show summer courses in available on center site only
        if (settings.SITE_ID != settings.CENTER_SITE_ID and
                current_term == SEMESTER_TYPES.summer):
            available = available.exclude(semester__type=SEMESTER_TYPES.summer)
        enrolled_in_current_term = {e.course_offering_id for e in
                                    enrolled_ongoing}
        available = [co for co in available if co.pk not in
                     enrolled_in_current_term]
        context = {
            "course_list_available": available,
            "enrollments_ongoing": enrolled_ongoing,
            "enrollments_archive": enrolled_archive,
            # FIXME: what about custom template tag for this?
            # TODO: Add util method
            "current_term": "{} {}".format(SEMESTER_TYPES[current_term],
                                           current_year).capitalize()
        }
        return context


class CourseVideoListView(generic.ListView):
    model = CourseOffering
    template_name = "learning/courses_video_list.html"
    context_object_name = 'course_list'

    def get_queryset(self):
        return (self.model.objects
                .filter(is_published_in_video=True)
                .order_by('-semester__year', 'semester__type')
                .select_related('course', 'semester'))

    def get_context_data(self, **kwargs):
        context = (super(CourseVideoListView, self)
                   .get_context_data(**kwargs))
        full = context[self.context_object_name]
        chunks = []
        for i in range(0, len(full), 3):
            chunks.append(full[i:i + 3])
        context['course_list_chunks'] = chunks
        return context


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "learning/courses/detail.html"
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = (super(CourseDetailView, self)
                   .get_context_data(**kwargs))

        context['offerings'] = (CourseOffering.objects
                                .in_city(self.request.city_code)
                                .open_only(is_club_site())
                                .filter(course=self.object).all())
        return context


class CourseUpdateView(CuratorOnlyMixin, ProtectedFormMixin,
                       generic.UpdateView):
    model = Course
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated and user.is_curator


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['is_actual_teacher'] = (
            self.request.user.is_authenticated and
            self.request.user in (self.object
                                  .course_offering
                                  .teachers.all()))
        context['attachments'] = self.object.courseclassattachment_set.all()
        return context


class CourseClassCreateUpdateMixin(TeacherOnlyMixin):
    model = CourseClass
    form_class = CourseClassForm
    template_name = "learning/forms/course_class.html"

    def get_course_offering(self):
        return get_co_from_query_params(self.kwargs, self.request.city_code)

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = kwargs.get("course_offering", self.get_course_offering())
        if not co:
            raise Http404('Course offering not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course_offering"] = co
        kwargs["initial"] = self.get_initial(**kwargs)
        return form_class(**kwargs)

    @staticmethod
    def is_form_allowed(user, course_offering):
        return user.is_curator or user in course_offering.teachers.all()

    def get_initial(self, **kwargs):
        return None

    # TODO: add atomic
    def form_valid(self, form):
        self.object = form.save()
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return_url = self.request.GET.get('back')
        if return_url == 'timetable':
            return reverse('timetable_teacher')
        if return_url == 'course_offering':
            return self.object.course_offering.get_absolute_url()
        if return_url == 'calendar':
            return reverse('calendar_teacher')
        elif "_addanother" in self.request.POST:
            return self.object.course_offering.get_create_class_url()
        else:
            return super(CourseClassCreateUpdateMixin, self).get_success_url()


class CourseClassCreateView(CourseClassCreateUpdateMixin, CreateView):

    def get_initial(self, **kwargs):
        # TODO: Add tests for initial data after discussion
        course_offering = kwargs["course_offering"]
        previous_class = (CourseClass.objects
                          .filter(course_offering=course_offering.pk)
                          .defer("description")
                          .order_by("-date", "starts_at")
                          .first())
        if previous_class is not None:
            return {
                "type": previous_class.type,
                "venue": previous_class.venue,
                "starts_at": previous_class.starts_at,
                "ends_at": previous_class.ends_at,
                "date": previous_class.date + datetime.timedelta(weeks=1)
            }
        return None

    def get_success_url(self):
        msg = _("The class '%s' was successfully created.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super(CourseClassCreateView, self).get_success_url()

    def post(self, request, *args, **kwargs):
        """Teachers can't add new classes if course already completed"""
        is_curator = self.request.user.is_curator
        co = self.get_course_offering()
        if not co or (not is_curator and co.is_completed):
            return HttpResponseForbidden()
        form = self.get_form(data=request.POST, files=request.FILES,
                             course_offering=co)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class CourseClassUpdateView(CourseClassCreateUpdateMixin, UpdateView):
    def get_success_url(self):
        msg = _("The class '%s' was successfully updated.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super(CourseClassUpdateView, self).get_success_url()


class CourseClassAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                      DeleteView):
    model = CourseClassAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated and user.is_curator) or \
               (user in obj.course_class.course_offering.teachers.all())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        # TODO: move to model method
        os.remove(self.object.material.path)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.course_class.get_update_url()


class CourseClassDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                            DeleteView):
    model = CourseClass
    template_name = "learning/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"

    def get_queryset(self):
        return (Venue.objects
                .filter(sites__pk=settings.SITE_ID)
                .filter(Q(city_id=self.request.city_code) |
                        Q(city__isnull=True)))


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"


# Note: Looks like shit
class AssignmentTeacherListView(TeacherOnlyMixin, generic.ListView):
    model = StudentAssignment
    context_object_name = 'student_assignment_list'
    template_name = "learning/assignment_list_teacher.html"
    user_type = 'teacher'
    filter_by_grades = (
        ("all", _("All")),  # Default
        ("no", _("Without grades")),
        ("yes", _("With grades")),
    )
    filter_by_comments = (
        ("any", _("No matter")),
        ("student", _("From student")),
        ("teacher", _("From teacher")),
        ("empty", _("Without comments")),
    )

    def get_queryset(self):
        # TODO: Show cs center courses on club site?
        filters = self.prepare_queryset_filters()
        return (
            StudentAssignment.objects
            .filter(**filters)
            .select_related('assignment',
                            'assignment__course_offering',
                            'assignment__course_offering__course',
                            'assignment__course_offering__semester',
                            'student')
            # Hide fat fields
            # FIXME: This is shit. With .values() I can retrieve only fields that I need and without .select_related
            .defer("assignment__text",
                   "student__university",
                   "student__comment",
                   "assignment__course_offering__description",
                   "assignment__course_offering__description_ru",
                   "assignment__course_offering__description_en",
                   "assignment__course_offering__course__description",
                   "assignment__course_offering__course__description_ru",
                   "assignment__course_offering__course__description_en", )
            .order_by('assignment__deadline_at', 'modified'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms"] = self.all_terms
        context["course_offerings"] = self.course_offerings
        context["assignments"] = self.assignments
        context["filter_by_grades"] = self.filter_by_grades
        context["filter_by_comments"] = self.filter_by_comments
        # Url for assignment filter
        query_tuple = [
            ('term', self.query["term"]),
            ('course', self.query["course_slug"]),
            ('grades', self.query["grades"]),
            ('comment', self.query["comment"]),
            ('assignment', ""),  # should be the last one
        ]
        self.query["form_url"] = "{}?{}".format(
            reverse("assignment_list_teacher"),
            urlencode(OrderedDict(query_tuple))
        )
        context["query"] = self.query
        return context

    def prepare_queryset_filters(self):
        """
        We process GET-query in optimistic way - assume that invalid data 
        comes very rarely.
        Process order of GET-params:
            term -> course -> assignment -> grade -> comment
        If query value invalid -> redirect to entry page.
        Also, we collect data for filter widgets.

        1. Get all courses for authenticated user (we should fallback to 
        previous term if no readings in current term)
        2. Collect all available terms (used in filter widget)
        3. Get term by `term` GET-param if valid or the latest one from step 2.
        4. Get courses for resulting term (used in filter widget)
        5. Get course offering by `course` GET-param if valid or get one from 
        list of courses for resulting term (step 4)
        6. Get assignments for resulting course (used in filter)
        7. Get assignment by `assignment` GET-param or latest from step 6.
        8. Set filters by resulting assignment, grade and last comment.
        """
        filters = {}
        teacher_all_course_offerings = self._get_all_teacher_course_offerings()
        all_terms = set(c.semester for c in teacher_all_course_offerings)
        all_terms = sorted(all_terms, key=lambda t: -t.index)
        # Try to get course offerings for requested term
        query_term_index = self._get_requested_term_index(all_terms)
        course_offerings = [c for c in teacher_all_course_offerings
                            if c.semester.index == query_term_index]
        # Try to get assignments for requested course_offering
        query_co = self._get_requested_course_offering(course_offerings)
        # FIXME: attach course offering or pass it to deadline_at_local
        assignments = list(
            Assignment.objects
            .filter(notify_teachers__teacher=self.request.user,
                    course_offering=query_co)
            .only("pk", "deadline_at", "title", "course_offering_id")
            .order_by("-deadline_at"))
        query_assignment = self._get_requested_assignment(assignments)
        if query_assignment:
            filters["assignment"] = query_assignment
        # Set filter by grade
        query_grade, filter_name, filter_value = self._get_filter_by_grade()
        if filter_name:
            filters[filter_name] = filter_value
        # Set filter by comment
        query_comment, filter_name, filter_value = self._get_filter_by_status()
        if filter_name:
            filters[filter_name] = filter_value

        # Cache to avoid additional queries to DB
        self.all_terms = all_terms
        self.course_offerings = course_offerings
        self.assignments = assignments
        self.query = {
            "course_slug": query_co.course.slug,
            "term": query_co.semester.slug,
            "assignment": query_assignment,
            "grades": query_grade,
            "comment": query_comment
        }
        return filters

    def _get_filter_by_grade(self):
        filter_name, filter_value = None, None
        query_value = self.request.GET.get("grades", "all")
        # FIXME: validate GET-params in separated method? and redirect?
        if query_value not in (k for k, v in self.filter_by_grades):
            query_value = "all"
        if query_value == "no":
            filter_name, filter_value = "grade__isnull", True
        elif query_value == "yes":
            filter_name, filter_value = "grade__isnull", False
        # FIXME: Может не устанавливать его вообще :<
        return query_value, filter_name, filter_value

    def _get_filter_by_status(self):
        filter_name, filter_value = None, None
        query_value = self.request.GET.get("comment", "any")
        if query_value not in (k for k, v in self.filter_by_comments):
            query_value = "any"
        if query_value == "student":
            filter_name = "last_comment_from"
            filter_value = self.model.LAST_COMMENT_STUDENT
        elif query_value == "teacher":
            filter_name = "last_comment_from"
            filter_value = self.model.LAST_COMMENT_TEACHER
        elif query_value == "empty":
            filter_name = "last_comment_from"
            filter_value = self.model.LAST_COMMENT_NOBODY
        return query_value, filter_name, filter_value

    def _get_all_teacher_course_offerings(self):
        """Returns all course offerings for authenticated user"""
        u = self.request.user
        cs = (CourseOffering.objects
              .filter(teachers=u)
              .select_related("course", "semester")
              .order_by("semester__index", "course__name"))
        if not cs:
            logger.warning("Teacher {} has no course sessions".format(u))
            self._redirect_to_course_list()
        return cs

    def _get_requested_term_index(self, all_terms):
        """
        Calculate term index from `term` and `year` GET-params.
        If term index not presented in teachers term_list, redirect
        to the latest available valid term from this list.
        """
        assert len(all_terms) > 0
        query_term = self.request.GET.get("term")
        if not query_term:
            # Terms in descending order, choose the latest one
            return all_terms[0].index
        try:
            year, term_type = query_term.split("-")
            year = int(year)
            if year < FOUNDATION_YEAR:  # invalid GET-param value
                raise ValidationError("Wrong year value")
            if term_type not in SEMESTER_TYPES:
                raise ValidationError("Wrong term type")
            term = next((t for t in all_terms if
                         t.type == term_type and t.year == year), None)
            if not term:
                raise ValidationError("Term not presented among available")
        except (ValueError, ValidationError):
            raise Redirect(to=reverse("assignment_list_teacher"))
        return term.index

    def _get_requested_course_offering(self, course_offerings):
        assert len(course_offerings) > 0
        """Get requested course_offering by GET-param `course`"""
        course_slug = self.request.GET.get("course", "")
        try:
            co = next(c for c in course_offerings if
                      c.course.slug == course_slug)
        except StopIteration:
            # TODO: get term and redirect to entry page
            co = course_offerings[0]
        return co

    def _get_requested_assignment(self, assignments):
        try:
            assignment_id = int(self.request.GET.get("assignment", ""))
        except ValueError:
            # FIXME: Ищем ближайшее, где должен наступить дедлайн
            assignment_id = next((a.pk for a in assignments), False)
        return next((a for a in assignments if a.pk == assignment_id),
                    None)

    def _redirect_to_course_list(self):
        messages.info(self.request,
                      _("You were redirected from Assignments due to "
                        "empty course list."),
                      extra_tags='timeout')
        raise Redirect(to=reverse("course_list_teacher"))


class AssignmentTeacherDetailView(TeacherOnlyMixin,
                                  generic.DetailView):
    model = Assignment
    template_name = "learning/assignment_detail_teacher.html"
    context_object_name = 'assignment'

    def get_queryset(self):
        return (self.model.objects
                .select_related('course_offering',
                                'course_offering__course',
                                'course_offering__semester')
                .prefetch_related('assignmentattachment_set'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))

        is_actual_teacher = (
            self.request.user in (self.object.course_offering.teachers.all()))
        if not is_actual_teacher and (not self.request.user.is_authenticated
                                      or not self.request.user.is_curator):
            raise PermissionDenied
        context['a_s_list'] = \
            (StudentAssignment.objects
             .filter(assignment__pk=self.object.pk)
             .select_related('assignment',
                             'assignment__course_offering',
                             'assignment__course_offering__course',
                             'assignment__course_offering__semester',
                             'student')
             .prefetch_related('student__groups'))
        return context


# FIXME: rewrite with vanilla view
class StudentAssignmentDetailMixin(object):
    model = AssignmentComment
    template_name = "learning/assignment_submission_detail.html"
    form_class = AssignmentCommentForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(
            StudentAssignment
                .objects
                .filter(pk=pk)
                .select_related('assignment',
                                'student',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester')
                .prefetch_related('assignment__course_offering__teachers',
                                  'assignment__assignmentattachment_set'))

        # Not sure if it's the best place for this, but it's the simplest one
        (AssignmentNotification.unread
         .filter(student_assignment=a_s, user=self.request.user)
         .update(is_unread=False))

        self._additional_permissions_check(a_s=a_s)

        context['a_s'] = a_s
        context['course_offering'] = a_s.assignment.course_offering
        context['user_type'] = self.user_type

        comments = (AssignmentComment.objects.filter(student_assignment=a_s)
                    .select_related('author')
                    .order_by('created'))
        first_comment_after_deadline = None
        assignment_deadline = (a_s.assignment.deadline_at +
                               datetime.timedelta(minutes=1))
        for c in comments:
            if first_comment_after_deadline is None \
                    and c.created >= assignment_deadline:
                first_comment_after_deadline = c.pk
        # Dynamically replace label
        if (not comments and context['user_type'] == 'student' and
                not a_s.assignment.is_online):
            context['form'].fields.get('text').label = _("Add solution")

        context['first_comment_after_deadline'] = first_comment_after_deadline
        context['comments'] = comments
        context['one_teacher'] = (a_s
                                  .assignment
                                  .course_offering
                                  .teachers
                                  .count() == 1)
        context['hashes_json'] = comment_persistence.get_hashes_json()
        return context

    def _additional_permissions_check(self, *args, **kwargs):
        pass

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(StudentAssignment.objects.filter(pk=pk))
        comment = form.save(commit=False)
        comment.student_assignment = a_s
        comment.author = self.request.user
        comment.save()
        comment_persistence.report_saved(comment.text)
        return redirect(self.get_success_url())


class StudentAssignmentTeacherDetailView(TeacherOnlyMixin,
                                         StudentAssignmentDetailMixin,
                                         generic.CreateView):
    user_type = 'teacher'

    def get_context_data(self, *args, **kwargs):
        context = (super(StudentAssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))
        a_s = context['a_s']
        co = a_s.assignment.course_offering
        initial = {'grade': a_s.grade}
        is_actual_teacher = (
            self.request.user in (a_s
                                  .assignment
                                  .course_offering
                                  .teachers.all()))
        if not is_actual_teacher and not self.request.user.is_curator:
            raise PermissionDenied
        context['is_actual_teacher'] = is_actual_teacher
        context['grade_form'] = AssignmentGradeForm(
            initial, grade_max=a_s.assignment.grade_max)
        # TODO: Replace with 1 query
        base = (
            StudentAssignment.objects
                .filter(grade__isnull=True,
                        first_submission_at__isnull=False,
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
            a_s = get_object_or_404(StudentAssignment.objects.filter(pk=pk))
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
                messages.success(self.request, _("Grade successfully saved"),
                                 extra_tags='timeout')
                return redirect(a_s.get_teacher_url())
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(form.errors))
        else:
            return (super(StudentAssignmentTeacherDetailView, self)
                    .post(request, *args, **kwargs))

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        # TODO: get_teacher_url
        return reverse('a_s_detail_teacher', args=[pk])


class AssignmentCreateUpdateMixin(TeacherOnlyMixin):
    model = Assignment
    form_class = AssignmentForm
    template_name = "learning/assignment_form.html"

    def get_course_offering(self):
        return get_co_from_query_params(self.kwargs, self.request.city_code)

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = self.get_course_offering()
        if not co:
            raise Http404('Course offering not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course_offering"] = co
        return form_class(**kwargs)

    @staticmethod
    def is_form_allowed(user, course_offering):
        return user.is_curator or user in course_offering.teachers.all()

    def get_success_url(self):
        return reverse('assignment_detail_teacher', args=[self.object.pk])

    # TODO: Add atomic
    def form_valid(self, form):
        self.save_form(form)
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=self.object, attachment=attachment))
        return redirect(self.get_success_url())

    def save_form(self, form):
        raise NotImplementedError()


class AssignmentCreateView(AssignmentCreateUpdateMixin, CreateView):
    def save_form(self, form):
        self.object = form.save()
        # Set up notifications recipients setting
        course_offering = self.object.course_offering
        co_teachers = course_offering.courseofferingteacher_set.all()
        notify_teachers = [t.pk for t in co_teachers if t.notify_by_default]
        self.object.notify_teachers.add(*notify_teachers)


class AssignmentUpdateView(AssignmentCreateUpdateMixin, UpdateView):
    def save_form(self, form):
        self.object = form.save()


class AssignmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin, DeleteView):
    model = Assignment
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return reverse('assignment_list_teacher')

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


# TODO: add permissions tests! Or perhaps anyone can look outside comments if I missed something :<
# FIXME: replace with vanilla view
class AssignmentCommentUpdateView(generic.UpdateView):
    model = AssignmentComment
    pk_url_kwarg = 'comment_pk'
    context_object_name = "comment"
    template_name = "learning/_modal_submission_comment.html"
    form_class = AssignmentModalCommentForm

    def form_valid(self, form):
        self.object = form.save()
        html = render_markdown(self.object.text)
        return JsonResponse({"success": 1,
                             "id": self.object.pk,
                             "html": html})

    def form_invalid(self, form):
        return JsonResponse({"success": 0, "errors": form.errors})

    def check_permissions(self, comment):
        # Allow view/edit own comments to teachers and all to curators
        if not self.request.user.is_curator:
            is_teacher = self.request.user.is_teacher
            if comment.author_id != self.request.user.pk or not is_teacher:
                raise PermissionDenied
            # Check comment not in stale state for edit
            if comment.is_stale_for_edit():
                raise PermissionDenied

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_permissions(self.object)
        return super(BaseUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_permissions(self.object)
        return super(BaseUpdateView, self).post(request, *args, **kwargs)


class AssignmentAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                     DeleteView):
    model = AssignmentAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_curator or
                user in obj.assignment.course_offering.teachers.all())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        os.remove(self.object.attachment.path)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.assignment.get_update_url()


class GradebookDispatchView(generic.ListView):
    model = Semester

    class RedirectException(Exception):
        def __init__(self, url):
            self.url = url

    def get(self, request, *args, **kwargs):
        try:
            return super(GradebookDispatchView,
                         self).get(request, *args, **kwargs)
        except GradebookDispatchView.RedirectException as e:
            return HttpResponseRedirect(e.url)

    def get_co_queryset(self):
        return (CourseOffering.objects.select_related("course")
                .order_by("course__name"))

    def get_queryset(self):
        current_year, term_type = get_current_semester_pair()
        semester_index = get_term_index(current_year, term_type)
        # Skip to spring semester
        if term_type == Semester.TYPES.autumn:
            semester_index += SEMESTER_AUTUMN_SPRING_INDEX_OFFSET
        return (self.model.objects
            .filter(index__lte=semester_index)
            .exclude(type=Semester.TYPES.summer)
            .prefetch_related(
            Prefetch(
                "courseoffering_set",
                queryset=self.get_co_queryset(),
                to_attr="courseofferings"
            )
        ))


class GradebookCuratorDispatchView(CuratorOnlyMixin, GradebookDispatchView):
    template_name = "learning/gradebook/list_curator.html"

    def get_context_data(self, **kwargs):
        context = super(GradebookCuratorDispatchView,
                        self).get_context_data(**kwargs)
        semester_list = list(context["semester_list"])
        if not semester_list:
            return context
        # Check if we have only the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)
        context["semester_list"] = [(a, s) for s, a in
                                    utils.grouper(semester_list, 2)]
        return context


class GradebookTeacherDispatchView(TeacherOnlyMixin, GradebookDispatchView):
    """
    Redirect teacher to appropriate gradebook page if he has only
    one course offering in current term.
    """
    template_name = "learning/gradebook/list_teacher.html"

    def get_co_queryset(self):
        qs = super(GradebookTeacherDispatchView, self).get_co_queryset()
        return qs.filter(teachers=self.request.user)

    def get_context_data(self, **kwargs):
        current_year, term_type = get_current_semester_pair()
        current_term_index = get_term_index(current_year, term_type)
        context = super(GradebookTeacherDispatchView,
                        self).get_context_data(**kwargs)
        co_count = 0
        for semester in context["semester_list"]:
            if semester.index == current_term_index:
                if len(semester.courseofferings) == 1:
                    co = semester.courseofferings[0]
                    url = reverse('markssheet_teacher', args=[
                        co.get_city(), co.course.slug, co.semester.year,
                        co.semester.type
                    ])
                    raise GradebookDispatchView.RedirectException(url)
            co_count += len(semester.courseofferings)
        if not co_count:
            context["semester_list"] = []
        return context


# TODO: add transaction.atomic
class MarksSheetTeacherView(TeacherOnlyMixin, generic.FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook/form.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        self.student_assignments = None
        self.enrollment_list = None
        self.course_offering_list = None
        self.course_offering = None
        super(MarksSheetTeacherView, self).__init__(*args, **kwargs)
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form_class(self):
        try:
            semester_year = int(self.kwargs['semester_year'])
        except (ValueError, TypeError):
            raise Http404('Course offering not found')

        co_queryset = CourseOffering.objects
        if not self.request.user.is_curator:
            co_queryset = co_queryset.filter(teachers=self.request.user)
        # TODO: add tests
        city_code = self.kwargs['city'].lower()
        co_queryset = co_queryset.filter(city=city_code)
        try:
            course_offering = (co_queryset
                               .select_related('semester', 'course')
                               .get(course__slug=self.kwargs['course_slug'],
                                    semester__type=self.kwargs['semester_type'],
                                    semester__year=semester_year))
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        self.course_offering = course_offering

        # Sacrifice attributes access for better performance
        student_assignments = (
            StudentAssignment.objects
                .filter(assignment__course_offering=course_offering)
                .values("pk",
                        "grade",
                        "first_submission_at",
                        "assignment__pk",
                        "assignment__title",
                        "assignment__is_online",
                        "assignment__grade_max",
                        "assignment__grade_min",
                        "student__pk")
                .order_by("assignment__pk",
                          "student__pk")
        )
        self.student_assignments = student_assignments

        enrollment_list = (Enrollment.active
                           .filter(course_offering=course_offering)
                           .select_related("student"))
        self.enrollment_list = enrollment_list

        course_offering_list = (co_queryset
                                .order_by('-semester__year',
                                          '-semester__type',
                                          '-pk')
                                .select_related('semester', 'course'))
        self.course_offering_list = course_offering_list

        return (GradeBookFormFactory.build_form_class(student_assignments,
                                                      enrollment_list))

    def get_initial(self):
        return (GradeBookFormFactory
                .transform_to_initial(self.student_assignments,
                                      self.enrollment_list))

    def get_success_url(self):
        co = self.course_offering
        if self.is_for_staff:
            url_name = 'staff:course_markssheet_staff'
        else:
            url_name = 'markssheet_teacher'
        messages.info(self.request, _('Gradebook successfully saved.'),
                      extra_tags='timeout')
        return reverse(url_name, args=[co.get_city(),
                                       co.course.slug,
                                       co.semester.year,
                                       co.semester.type])

    def form_valid(self, form):
        a_s_index, enrollment_index = \
            GradeBookFormFactory.build_indexes(self.student_assignments,
                                               self.enrollment_list)
        final_grade_updated = False
        for field in form.changed_data:
            if field in a_s_index:
                a_s = a_s_index[field]
                StudentAssignment.objects.filter(pk=a_s["pk"]).update(
                    grade=form.cleaned_data[field])
                continue
            # Looking for final_grade_*
            elif field in enrollment_index:
                final_grade_updated = True
                enrollment = enrollment_index[field]
                enrollment.grade = form.cleaned_data[field]
                enrollment.save()
                continue
        if final_grade_updated:
            self.recalculate_grading_type()
        return redirect(self.get_success_url())

    def recalculate_grading_type(self):
        """Update grading type for binded course offering if needed"""
        es = (Enrollment.active
              .filter(course_offering=self.course_offering)
              .values_list("grade", flat=True))
        grading_type = GRADING_TYPES.default
        if not any(filter(lambda g: g in [GRADES.good, GRADES.excellent], es)):
            grading_type = GRADING_TYPES.binary
        if self.course_offering.grading_type != grading_type:
            self.course_offering.grading_type = grading_type
            self.course_offering.save()

    def get_context_data(self, *args, **kwargs):
        context = (super(MarksSheetTeacherView, self)
                   .get_context_data(*args, **kwargs))
        context['course_offering'] = self.course_offering
        context['course_offering_list'] = self.course_offering_list
        context['user_type'] = self.user_type

        students = OrderedDict()
        assignments = OrderedDict()

        def get_final_grade_widget(enrollment_pk):
            key = GradeBookFormFactory.FINAL_GRADE_PREFIX.format(enrollment_pk)
            return context['form'][key]

        for enrollment in self.enrollment_list:
            student_id = enrollment.student_id
            if student_id not in students:
                students[student_id] = OrderedDict({
                    "student": enrollment.student,
                    "grade": get_final_grade_widget(enrollment.pk),
                    "total": 0
                })

        for a_s in self.student_assignments:
            student_id = a_s["student__pk"]
            assignment_id = a_s["assignment__pk"]
            # The student unsubscribed from the course
            if student_id not in students:
                continue

            if assignment_id not in assignments:
                assignments[assignment_id] = {
                    "header": {
                        "pk": a_s["assignment__pk"],
                        "title": a_s["assignment__title"],
                        "is_online": a_s["assignment__is_online"],
                        "grade_min": a_s["assignment__grade_min"],
                        "grade_max": a_s["assignment__grade_max"],
                    },
                    "students": OrderedDict(((sid, None) for sid in students))
                }
            assignment = assignments[assignment_id]

            state = None
            # FIXME: duplicated logic from is_passed method!
            a_s["is_passed"] = a_s["first_submission_at"] is not None
            if assignment["header"]["is_online"]:
                state_value = StudentAssignment.calculate_state(
                    a_s["grade"],
                    assignment["header"]["is_online"],
                    a_s["is_passed"],
                    assignment["header"]["grade_min"],
                    assignment["header"]["grade_max"],
                )
                if a_s["grade"] is not None:
                    state = "{0}/{1}".format(a_s["grade"],
                                             assignment["header"]["grade_max"])
                else:
                    state = StudentAssignment.SHORT_STATES[state_value]
            assignment["students"][student_id] = {
                "pk": a_s["pk"],
                "grade": a_s["grade"] if a_s["grade"] is not None else "",
                "is_passed": a_s["is_passed"],  # FIXME: useless?
                "state": state
            }

            if a_s["grade"] is not None:
                students[student_id]["total"] += int(a_s["grade"])

        for assignment in assignments.values():
            # we should check for "assignment consistency": that all
            # student assignments are presented
            assert any(s is not None for s in assignment["students"])

        context['students'] = students
        context['assignments'] = assignments
        # Magic "100" constant - width of .assignment column
        context['assignments_width'] = len(assignments) * 100

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
        except (ValueError, TypeError):
            raise Http404('Course offering not found')
        if request.user.is_authenticated and request.user.is_curator:
            base_qs = CourseOffering.objects
        else:
            base_qs = CourseOffering.objects.filter(teachers=request.user)

        # TODO: add tests
        city_code = self.kwargs['city'].lower()
        base_qs = base_qs.filter(city=city_code)

        try:
            co = base_qs.get(
                course__slug=course_slug,
                semester__type=semester_type,
                semester__year=semester_year)
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        a_ss = (StudentAssignment.objects
                .filter(assignment__course_offering=co)
                .order_by('student', 'assignment')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))
        enrollments = (Enrollment.active
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
            if a_s.student not in structured:
                continue  # student isn't enrolled
            structured[a_s.student][a_s.assignment] = a_s.grade

        header = viewvalues(structured)
        # FIXME: raise StopIteration if no students found. Add test
        header = next(iter(header)).keys()
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
        writer.writerow(['Фамилия',
                         'Имя',
                         'Яндекс ID'] +
                        [a.title for a in header] +
                        ['Итоговая оценка'])
        for student, by_assignment in structured.items():
            writer.writerow(
                [(x if x is not None else '') for x in
                 itertools.chain([student.last_name, student.first_name,
                                  student.yandex_id],
                                 by_assignment.values(),
                                 [enrollment_grades[student]])])
        return response


class MarksSheetTeacherImportCSVFromStepicView(TeacherOnlyMixin, generic.View):
    """Import students grades from stepic platform"""

    def post(self, request, course_offering_pk, *args, **kwargs):
        filters = {"pk": course_offering_pk}
        if not request.user.is_curator:
            filters['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filters)
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByStepicID(request, assignment).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)


class MarksSheetTeacherImportCSVFromYandexView(TeacherOnlyMixin, generic.View):
    """Import students grades by yandex login"""

    def post(self, request, *args, **kwargs):
        filter = dict(pk=self.kwargs.get('course_offering_pk'))
        if not request.user.is_authenticated or not request.user.is_curator:
            filter['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filter)
        # FIXME: replace with util function, too much args to pass
        url = reverse('markssheet_teacher',
                      args=[co.get_city(),
                            co.course.slug,
                            co.semester.year,
                            co.semester.type])
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByYandexLogin(request, assignment).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)


class NonCourseEventDetailView(generic.DetailView):
    model = NonCourseEvent
    context_object_name = 'event'
    template_name = "learning/noncourseevent_detail.html"


class OnlineCoursesListView(generic.ListView):
    context_object_name = 'courses'
    model = OnlineCourse

    def get_context_data(self, **kwargs):
        context = super(OnlineCoursesListView, self).get_context_data(**kwargs)
        context["recent_courses"] = filter(
            lambda c: not c.is_self_paced and (not c.end or c.end > timezone.now()),
            context[self.context_object_name])
        context["self_paced_courses"] = sorted(filter(
            lambda c: c.is_self_paced,
            context[self.context_object_name]), key=lambda c: c.name)
        context["archive_courses"] = filter(
            lambda c: c.end and c.end <= timezone.now() and not c.is_self_paced,
            context[self.context_object_name]
        )
        return context

    def get_queryset(self):
        return OnlineCourse.objects.order_by("is_self_paced", "-start", "name")


class InternationalSchoolsListView(generic.ListView):
    model = InternationalSchool
    context_object_name = 'schools'
    template_name = "learning/international_schools.html"

    def get_queryset(self):
        return InternationalSchool.objects.order_by("-deadline")


class AssignmentAttachmentDownloadView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
        except IndexError:
            raise Http404

        response = HttpResponse()

        if attachment_type == ASSIGNMENT_TASK_ATTACHMENT:
            qs = AssignmentAttachment.objects.filter(pk=pk)
            assignment_attachment = get_object_or_404(qs)
            file_field = assignment_attachment.attachment
        elif attachment_type == ASSIGNMENT_COMMENT_ATTACHMENT:
            qs = AssignmentComment.objects.filter(pk=pk)
            if not request.user.is_teacher and not request.user.is_curator:
                qs = qs.filter(student_assignment__student_id=request.user.pk)
            comment = get_object_or_404(qs)
            file_field = comment.attached_file
        else:
            return HttpResponseBadRequest()
        file_url = file_field.url
        file_name = os.path.basename(file_field.name)
        # Try to generate html version of ipynb
        if self.request.GET.get("html", False):
            html_ext = ".html"
            _, ext = posixpath.splitext(file_name)
            if ext == ".ipynb":
                ipynb_src_path = file_field.path
                converted_path = ipynb_src_path + html_ext
                if not os.path.exists(converted_path):
                    # TODO: move html_exporter to separated module
                    # TODO: disable warnings 404 for css and ico in media folder for ipynb files?
                    html_exporter = nbconvert.HTMLExporter()
                    try:
                        nb_node, _ = html_exporter.from_filename(ipynb_src_path)
                        with open(converted_path, 'w') as f:
                            f.write(nb_node)
                    except FileNotFoundError:
                        pass
                # FIXME: if file doesn't exists - returns 404?
                file_name += html_ext
                response['X-Accel-Redirect'] = file_url + html_ext
                return response

        del response['Content-Type']
        # Content-Disposition doesn't have appropriate non-ascii symbols support
        response['Content-Disposition'] = "attachment; filename={}".format(
            file_name)
        response['X-Accel-Redirect'] = file_url
        return response
