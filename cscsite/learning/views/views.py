import datetime
import logging
import os
import posixpath
from collections import OrderedDict
from time import localtime
from typing import Optional
from urllib.parse import urlencode

import nbconvert
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Prefetch, When, Value, Case, \
    prefetch_related_objects
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseRedirect, HttpResponseForbidden
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.edit import BaseUpdateView
from vanilla import CreateView, UpdateView, DeleteView, ListView, TemplateView

from core import comment_persistence
from core.exceptions import Redirect
from core.utils import hashids, render_markdown, is_club_site
from core.views import ProtectedFormMixin, LoginRequiredMixin
from learning import utils
from learning.calendar import CalendarQueryParams
from learning.forms import CourseClassForm, CourseForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm, \
    AssignmentModalCommentForm
from learning.models import MetaCourse, CourseClass, Course, Venue, \
    Enrollment, Assignment, AssignmentAttachment, \
    StudentAssignment, AssignmentComment, \
    CourseClassAttachment, AssignmentNotification, \
    Semester, NonCourseEvent, \
    OnlineCourse, InternationalSchool, CourseTeacher
from learning.permissions import access_role, CourseRole
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT, \
    ASSIGNMENT_TASK_ATTACHMENT, FOUNDATION_YEAR, SEMESTER_TYPES
from learning.utils import get_current_term_pair, get_term_index, now_local, \
    get_terms_for_calendar_month, grouper
from learning.viewmixins import TeacherOnlyMixin, StudentOnlyMixin, \
    CuratorOnlyMixin
from learning.views.generic import CalendarGenericView
from learning.views.utils import get_teacher_city_code, \
    get_co_from_query_params, get_student_city_code

logger = logging.getLogger(__name__)

DROP_ATTACHMENT_LINK = """
<a href="{0}"><i class="fa fa-trash-o"></i>&nbsp;{1}</a>"""

__all__ = [
    # mixins
    'AssignmentProgressBaseView',
    # views
    'TimetableTeacherView', 'TimetableStudentView', 'CalendarStudentFullView',
    'CalendarStudentView', 'CalendarTeacherFullView', 'CalendarTeacherView',
    'CoursesListView', 'CourseTeacherListView', 'CourseStudentListView',
    'CourseVideoListView', 'CourseDetailView', 'CourseUpdateView',
    'CourseClassDetailView', 'CourseClassCreateView', 'CourseClassUpdateView',
    'CourseClassAttachmentDeleteView', 'CourseClassDeleteView',
     'VenueListView', 'VenueDetailView', 'AssignmentTeacherListView',
    'AssignmentTeacherDetailView', 'StudentAssignmentTeacherDetailView',
    'AssignmentCreateView', 'AssignmentUpdateView', 'AssignmentDeleteView',
    'AssignmentCommentUpdateView', 'AssignmentAttachmentDeleteView',
    'NonCourseEventDetailView', 'OnlineCoursesListView',
    'InternationalSchoolsListView', 'AssignmentAttachmentDownloadView',
]


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
                                'course_offering__meta_course',
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
                                'course_offering__meta_course',
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
    Shows non-course events and classes filtered by authenticated student city.
    """
    def get_user_city(self):
        return get_student_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        student_city_code = kwargs.get('user_city_code')
        return [self._get_classes(year, month, student_city_code),
                self._get_non_course_events(year, month, student_city_code)]

    @staticmethod
    def _get_non_course_events(year, month, student_city_code):
        return (NonCourseEvent.objects
                .for_calendar()
                .for_city(student_city_code)
                .in_month(year, month))

    def _get_classes(self, year, month, student_city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_city(student_city_code))


class CalendarStudentView(CalendarStudentFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def _get_classes(self, year, month, student_city_code):
        qs = super()._get_classes(year, month, student_city_code)
        return qs.for_student(self.request.user)


class CalendarTeacherFullView(TeacherOnlyMixin, CalendarGenericView):
    """Shows non-course events and classes filtered by cities where
    authenticated teacher has course sessions."""

    def get_user_city(self):
        return get_teacher_city_code(self.request)

    def get_teacher_cities(self, year, month):
        if is_club_site():
            return [self.get_user_city()]
        # Collect all cities where authenticated teacher has sessions
        terms_in_month = get_terms_for_calendar_month(year, month)
        term_indexes = [get_term_index(*term) for term in terms_in_month]
        cities = list(Course.objects
                      .filter(semester__index__in=term_indexes)
                      .for_teacher(self.request.user)
                      .values_list("city_id", flat=True)
                      .order_by('city_id')
                      .distinct())
        if not cities:
            cities = [self.get_user_city()]
        return cities

    def get_events(self, year, month, **kwargs):
        cities = self.get_teacher_cities(year, month)
        return [self._get_classes(year, month, cities),
                self._get_non_course_events(year, month, cities)]

    @staticmethod
    def _get_non_course_events(year, month, cities):
        return (NonCourseEvent.objects
                .for_calendar()
                .in_cities(cities)
                .in_month(year, month))

    def _get_classes(self, year, month, cities):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_cities(cities))


class CalendarTeacherView(CalendarTeacherFullView):
    """
    Shows all non-course events and classes for courses in which authenticated
    teacher participated.
    """
    calendar_type = 'teacher'
    template_name = "learning/calendar.html"

    def _get_classes(self, year, month, cities):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .for_teacher(self.request.user))


class CoursesListView(generic.ListView):
    model = Semester
    template_name = "learning/courses/offerings.html"

    def get_queryset(self):
        cos_qs = (Course.objects
                  .select_related('meta_course')
                  .prefetch_related('teachers')
                  .order_by('meta_course__name'))
        if is_club_site():
            cos_qs = cos_qs.in_city(self.request.city_code)
        else:
            cos_qs = cos_qs.in_center_branches()
        prefetch_cos = Prefetch('courseoffering_set',
                                queryset=cos_qs,
                                to_attr='courseofferings')
        q = (Semester.objects.prefetch_related(prefetch_cos))
        # Courses in CS Center started at 2011 year
        if not is_club_site():
            q = (q.filter(year__gte=2011)
                .exclude(type=Case(
                    When(year=2011, then=Value(Semester.TYPES.spring)),
                    default=Value(""))))
        return q

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class CourseTeacherListView(TeacherOnlyMixin, generic.ListView):
    model = Course
    context_object_name = 'course_list'
    template_name = "learning/courses/teaching_list.html"

    def get_queryset(self):
        return (Course.objects
                .filter(teachers=self.request.user)
                .select_related('meta_course', 'semester')
                .prefetch_related('teachers')
                .order_by('-semester__index', 'meta_course__name'))


class CourseStudentListView(StudentOnlyMixin, generic.TemplateView):
    model = Course
    context_object_name = 'course_list'
    template_name = "learning/courses/learning_my_courses.html"

    def get_context_data(self, **kwargs):
        city_code = get_student_city_code(self.request)
        # Student enrollments
        student_enrollments = (Enrollment.active
                               .filter(student_id=self.request.user)
                               .select_related("course_offering")
                               .only('id', 'grade', 'course_offering_id',
                                     'course_offering__grading_type'))
        student_enrolled_in = {e.course_offering_id: e for e in
                               student_enrollments}
        # 1. Union courses from current term and which student enrolled in
        current_year, current_term = get_current_term_pair(city_code)
        current_term_index = get_term_index(current_year, current_term)
        in_current_term = Q(semester__index=current_term_index)
        enrolled_in = Q(id__in=list(student_enrolled_in))
        # Hide summer courses on CS Club site until student enrolled in
        if is_club_site():
            in_current_term &= ~Q(semester__type=SEMESTER_TYPES.summer)
        course_offerings = (Course.objects
                            .get_offerings_base_queryset()
                            .in_city(city_code)
                            .filter(in_current_term | enrolled_in))
        # 2. And split them by type.
        ongoing_enrolled, ongoing_rest, archive_enrolled = [], [], []
        for co in course_offerings:
            if co.semester.index == current_term_index:
                if co.pk in student_enrolled_in:
                    # TODO: add `enrollments` to context and get grades explicitly in tmpl
                    co.enrollment = student_enrolled_in[co.pk]
                    ongoing_enrolled.append(co)
                else:
                    ongoing_rest.append(co)
            else:
                co.enrollment = student_enrolled_in[co.pk]
                archive_enrolled.append(co)
        context = {
            "ongoing_rest": ongoing_rest,
            "ongoing_enrolled": ongoing_enrolled,
            "archive_enrolled": archive_enrolled,
            # FIXME: what about custom template tag for this?
            # TODO: Add util method
            "current_term": "{} {}".format(SEMESTER_TYPES[current_term],
                                           current_year).capitalize()
        }
        return context


class CourseVideoListView(ListView):
    model = Course
    template_name = "learning/courses_video_list.html"
    context_object_name = 'course_list'

    def get_queryset(self):
        return (Course.objects
                .filter(is_published_in_video=True)
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full = context[self.context_object_name]
        context['course_list_chunks'] = grouper(full, 3)
        return context


class CourseDetailView(generic.DetailView):
    model = MetaCourse
    template_name = "learning/courses/detail.html"
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = (Course.objects
              .select_related("meta_course", "semester", "city")
              .filter(meta_course=self.object))
        # Separate by city only on compsciclub.ru
        if is_club_site():
            qs = qs.in_city(self.request.city_code)
        else:
            qs = qs.in_center_branches()
        context['offerings'] = qs
        context["show_city"] = not is_club_site()
        return context


class CourseUpdateView(CuratorOnlyMixin, ProtectedFormMixin,
                       generic.UpdateView):
    model = MetaCourse
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated and user.is_curator


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'

    def get_queryset(self):
        return (CourseClass.objects
                .select_related("course_offering",
                                "course_offering__meta_course",
                                "course_offering__semester",
                                "venue")
                .in_city(self.request.city_code))

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
            return super().get_success_url()


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
        return super().get_success_url()

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
        return super().get_success_url()


class CourseClassAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                      DeleteView):
    model = CourseClassAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_curator or
                user in obj.course_class.course_offering.teachers.all())

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
class AssignmentTeacherListView(TeacherOnlyMixin, TemplateView):
    model = StudentAssignment
    context_object_name = 'student_assignment_list'
    template_name = "learning/assignment_list_teacher.html"
    user_type = 'teacher'
    # FIXME: rename
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

    def get_queryset(self, filters):
        # TODO: Show cs center courses on club site?
        return (
            StudentAssignment.objects
            .filter(**filters)
            .select_related("assignment", "student",)
            .only("id",
                  "grade",
                  "first_submission_at",
                  "student__first_name",
                  "student__last_name",
                  "assignment__id",
                  "assignment__course_offering_id",
                  "assignment__is_online",
                  "assignment__grade_min",
                  "assignment__grade_max",)
            .prefetch_related("student__groups",)
            .order_by('student__last_name', 'student__first_name'))

    def get_context_data(self, **kwargs):
        context = {
            "filter_by_grades": self.filter_by_grades,
            "filter_by_comments": self.filter_by_comments
        }
        filters = self.prepare_queryset_filters(context)
        if "assignment" in filters:
            course_offering_id = filters["assignment"].course_offering_id
            # TODO: select `deleted` instead?
            # TODO: move to separated method and return set
            qs = (Enrollment.active
                  .filter(course_offering_id=course_offering_id)
                  .values_list("student_id", flat=True))
            context["enrollments"] = set(qs)
        context["student_assignment_list"] = self.get_queryset(filters)
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

    def prepare_queryset_filters(self, context):
        """
        We process GET-query in optimistic way - assume that invalid data 
        comes very rarely.
        Processing order of GET-params:
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
        6. Collect assignments for resulting course (used in filter)
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
        context["all_terms"] = all_terms
        context["course_offerings"] = course_offerings
        context["assignments"] = assignments
        self.query = {
            "course_slug": query_co.meta_course.slug,
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
        cs = (Course.objects
              .filter(teachers=u)
              .select_related("meta_course", "semester")
              .order_by("semester__index", "meta_course__name"))
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
                      c.meta_course.slug == course_slug)
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
                                'course_offering__meta_course',
                                'course_offering__semester')
                .prefetch_related('assignmentattachment_set'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = access_role(co=self.object.course_offering,
                           request_user=self.request.user)
        if role not in [CourseRole.CURATOR, CourseRole.TEACHER]:
            raise PermissionDenied
        context['a_s_list'] = (
            StudentAssignment.objects
            .filter(assignment__pk=self.object.pk)
            .select_related('assignment',
                            'assignment__course_offering',
                            'assignment__course_offering__meta_course',
                            'assignment__course_offering__semester',
                            'student')
            .prefetch_related('student__groups'))
        return context


class AssignmentProgressBaseView(AccessMixin):
    model = AssignmentComment
    template_name = "learning/assignment_submission_detail.html"
    form_class = AssignmentCommentForm

    def handle_no_permission(self, request):
        """
        AccessMixin.handle_no_permission behavior was changed in Django 2.1
        Trying to save previous one.
        """
        # TODO: Remove AccessMixin
        return redirect_to_login(request.get_full_path(),
                                 settings.LOGIN_URL,
                                 REDIRECT_FIELD_NAME)

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permissions_coarse(request.user):
            return self.handle_no_permission(request)
        self.student_assignment = self.get_student_assignment()
        if not self.student_assignment:
            raise Http404
        if not self.has_permissions_precise(request.user):
            return self.handle_no_permission(request)
        return super().dispatch(request, *args, **kwargs)

    def get_student_assignment(self) -> Optional[StudentAssignment]:
        return (StudentAssignment.objects
                .filter(pk=self.kwargs['pk'])
                .select_related('student',
                                'assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__meta_course',
                                'assignment__course_offering__semester')
                .first())

    @staticmethod
    def _prefetch_data(student_assignment):
        prefetch_comments = Prefetch('assignmentcomment_set',
                                     queryset=(AssignmentComment.objects
                                               .select_related('author')
                                               .order_by('created')))
        prefetch_related_objects([student_assignment],
                                 prefetch_comments,
                                 'assignment__course_offering__teachers',
                                 'assignment__assignmentattachment_set')

    def get_context_data(self, form, **kwargs):
        sa = self.student_assignment
        # Since no need to prefetch data for POST-action, do it only here.
        self._prefetch_data(sa)
        # Not sure if it's the best place for this, but it's the simplest one
        user = self.request.user
        (AssignmentNotification.unread
         .filter(student_assignment=sa, user=user)
         .update(is_unread=False))
        # Let's consider last minute of deadline in favor of the student
        deadline_at = sa.assignment.deadline_at + datetime.timedelta(minutes=1)
        cs_after_deadline = (c for c in sa.assignmentcomment_set.all() if
                             c.created >= deadline_at)
        first_comment_after_deadline = next(cs_after_deadline, None)
        co = sa.assignment.course_offering
        tz_override = co.get_city_timezone()
        # For online courses format datetime in student timezone
        # Note, that this view available for teachers, curators and
        # enrolled students only
        if co.is_correspondence and (user.is_student_center or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_id]
        context = {
            'user_type': self.user_type,
            'a_s': sa,
            'form': form,
            'timezone': tz_override,
            'first_comment_after_deadline': first_comment_after_deadline,
            'one_teacher': sa.assignment.course_offering.teachers.count() == 1,
            'hashes_json': comment_persistence.get_hashes_json()
        }
        return context

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.student_assignment = self.student_assignment
        comment.author = self.request.user
        comment.save()
        comment_persistence.report_saved(comment.text)
        return redirect(self.get_success_url())


class StudentAssignmentTeacherDetailView(AssignmentProgressBaseView,
                                         CreateView):
    user_type = 'teacher'
    # FIXME: combine has_permissions_*
    def has_permissions_coarse(self, user):
        return user.is_curator or user.is_teacher

    def has_permissions_precise(self, user):
        co = self.student_assignment.assignment.course_offering
        role = access_role(co=co, request_user=user)
        return role in [CourseRole.TEACHER, CourseRole.CURATOR]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        a_s = self.student_assignment
        co = a_s.assignment.course_offering
        # Get next unchecked assignment
        base = (StudentAssignment.objects
                .filter(grade__isnull=True,
                        first_submission_at__isnull=False,
                        assignment__course_offering=co,
                        assignment__course_offering__teachers=self.request.user)
                .order_by('assignment__deadline_at', 'pk')
                .only('pk'))
        next_a_s = (base.filter(pk__gt=a_s.pk).first() or
                    base.filter(pk__lt=a_s.pk).first())
        context['next_a_s_pk'] = next_a_s.pk if next_a_s else None
        context['is_actual_teacher'] = self.request.user in co.teachers.all()
        context['grade_form'] = AssignmentGradeForm(
            initial={'grade': a_s.grade},
            grade_max=a_s.assignment.grade_max)
        return context

    def post(self, request, *args, **kwargs):
        # TODO: separate to update view
        if 'grading_form' in request.POST:
            a_s = self.student_assignment
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
                if a_s.grade is None:
                    messages.info(self.request,
                                  _("Grade was deleted"),
                                  extra_tags='timeout')
                else:
                    messages.success(self.request,
                                     _("Grade successfully saved"),
                                     extra_tags='timeout')
                return redirect(a_s.get_teacher_url())
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(form.errors))
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.student_assignment.get_teacher_url()


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
        co_teachers = course_offering.course_teachers.all()
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

        user = request.user
        if attachment_type == ASSIGNMENT_TASK_ATTACHMENT:
            file_field = self.get_task_attachment(pk)
            if file_field is None:
                return HttpResponseForbidden()
        elif attachment_type == ASSIGNMENT_COMMENT_ATTACHMENT:
            qs = AssignmentComment.objects.filter(pk=pk)
            if not user.is_teacher and not user.is_curator:
                qs = qs.filter(student_assignment__student_id=user.pk)
            # TODO: restrict access for teachers
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
                    except (FileNotFoundError, AttributeError):
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

    def get_task_attachment(self, attachment_id):
        """
        Curators, all course teachers and non-expelled enrolled students
        can download task attachments.
        """
        qs = (AssignmentAttachment.objects
              .filter(pk=attachment_id)
              .select_related("assignment", "assignment__course_offering"))
        assignment_attachment = get_object_or_404(qs)
        role = access_role(co=assignment_attachment.assignment.course_offering,
                           request_user=self.request.user)
        # User doesn't have private access to the task
        if role is not None and role != CourseRole.STUDENT_RESTRICT:
            return assignment_attachment.attachment
        return None
