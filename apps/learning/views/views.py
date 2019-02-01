import datetime
import logging
import os
import posixpath
from collections import OrderedDict
from itertools import chain
from typing import Optional, Union
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Prefetch, When, Value, Case, \
    prefetch_related_objects
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from nbconvert import HTMLExporter
from vanilla import CreateView, TemplateView

import courses.utils
from core import comment_persistence
from core.exceptions import Redirect
from core.settings.base import FOUNDATION_YEAR
from core.timezone import Timezone, CityCode
from core.urls import reverse
from core.utils import hashids, is_club_site
from core.views import LoginRequiredMixin
from courses.calendar import CalendarEvent
from courses.models import Course, Semester, CourseClass, \
    Assignment, AssignmentAttachment
from courses.settings import SemesterTypes
from courses.utils import get_current_term_pair, get_term_index, \
    get_terms_for_calendar_month
from courses.views.calendar import MonthEventsCalendarView
from learning.calendar import LearningCalendarEvent
from learning.forms import AssignmentCommentForm, AssignmentScoreForm
from learning.models import Enrollment, StudentAssignment, AssignmentComment, \
    AssignmentNotification, \
    Event
from learning.permissions import course_access_role, CourseRole
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT, \
    ASSIGNMENT_TASK_ATTACHMENT
from learning.views.utils import get_teacher_city_code, \
    get_student_city_code
from users.mixins import TeacherOnlyMixin, StudentOnlyMixin

logger = logging.getLogger(__name__)

DROP_ATTACHMENT_LINK = """
<a href="{0}"><i class="fa fa-trash-o"></i>&nbsp;{1}</a>"""

__all__ = [
    # mixins
    'AssignmentProgressBaseView',
    # views
    'CalendarTeacherFullView', 'CalendarTeacherPersonalView',
    'CoursesListView', 'CourseTeacherListView', 'CourseStudentListView',
    'AssignmentTeacherListView',
    'AssignmentTeacherDetailView', 'StudentAssignmentTeacherDetailView',
    'EventDetailView',
    'AssignmentAttachmentDownloadView',
    'AssignmentCommentAttachmentDownloadView'
]


class CalendarTeacherFullView(TeacherOnlyMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes filtered by the cities where
    authorized teacher has taught.
    """

    def get_default_timezone(self) -> Union[Timezone, CityCode]:
        return get_teacher_city_code(self.request)

    def get_teacher_cities(self, year, month):
        default_city = get_teacher_city_code(self.request)
        if is_club_site():
            return [default_city]
        # Collect all the cities where authorized teacher taught.
        terms_in_month = get_terms_for_calendar_month(year, month)
        term_indexes = [get_term_index(*term) for term in terms_in_month]
        cities = list(Course.objects
                      .filter(semester__index__in=term_indexes)
                      .for_teacher(self.request.user)
                      .values_list("city_id", flat=True)
                      .order_by('city_id')
                      .distinct())
        if not cities:
            cities = [default_city]
        return cities

    def get_events(self, year, month, **kwargs):
        cities = self.get_teacher_cities(year, month)
        return chain(
            (CalendarEvent(e) for e in self._get_classes(year, month, cities)),
            (LearningCalendarEvent(e) for e in
                self._get_events(year, month, cities))
        )

    @staticmethod
    def _get_events(year, month, cities):
        return (Event.objects
                .for_calendar()
                .in_cities(cities)
                .in_month(year, month))

    def _get_classes(self, year, month, cities):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_cities(cities))


class CalendarTeacherPersonalView(CalendarTeacherFullView):
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
        prefetch_cos = Prefetch('course_set',
                                queryset=cos_qs,
                                to_attr='courseofferings')
        q = (Semester.objects.prefetch_related(prefetch_cos))
        # Courses in CS Center started at 2011 year
        if not is_club_site():
            q = (q.filter(year__gte=2011)
                .exclude(type=Case(
                    When(year=2011, then=Value(SemesterTypes.SPRING)),
                    default=Value(""))))
        return q

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_list = [s for s in context["semester_list"]
                         if s.type != SemesterTypes.SUMMER]
        if not semester_list:
            context["semester_list"] = semester_list
            return context
        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == SemesterTypes.AUTUMN:
            semester = Semester(type=SemesterTypes.SPRING,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)
        # Hide empty pairs
        context["semester_list"] = [
            (a, s) for s, a in courses.utils.grouper(semester_list, 2) if \
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
                               .select_related("course")
                               .only('id', 'grade', 'course_id',
                                     'course__grading_type'))
        student_enrolled_in = {e.course_id: e for e in student_enrollments}
        # 1. Union courses from current term and which student enrolled in
        current_year, current_term = get_current_term_pair(city_code)
        current_term_index = get_term_index(current_year, current_term)
        in_current_term = Q(semester__index=current_term_index)
        enrolled_in = Q(id__in=list(student_enrolled_in))
        # Hide summer courses on CS Club site until student enrolled in
        if is_club_site():
            in_current_term &= ~Q(semester__type=SemesterTypes.SUMMER)
        course_offerings = (Course.objects
                            .get_offerings_base_queryset()
                            .in_city(city_code)
                            .filter(in_current_term | enrolled_in))
        # 2. And split them by type.
        ongoing_enrolled, ongoing_rest, archive_enrolled = [], [], []
        for course in course_offerings:
            if course.semester.index == current_term_index:
                if course.pk in student_enrolled_in:
                    # TODO: add `enrollments` to context and get grades explicitly in tmpl
                    course.enrollment = student_enrolled_in[course.pk]
                    ongoing_enrolled.append(course)
                else:
                    ongoing_rest.append(course)
            else:
                course.enrollment = student_enrolled_in[course.pk]
                archive_enrolled.append(course)
        context = {
            "ongoing_rest": ongoing_rest,
            "ongoing_enrolled": ongoing_enrolled,
            "archive_enrolled": archive_enrolled,
            # FIXME: what about custom template tag for this?
            # TODO: Add util method
            "current_term": "{} {}".format(SemesterTypes.values[current_term],
                                           current_year).capitalize()
        }
        return context


# Note: Looks like shit
class AssignmentTeacherListView(TeacherOnlyMixin, TemplateView):
    model = StudentAssignment
    context_object_name = 'student_assignment_list'
    template_name = "learning/teaching/assignment_list.html"
    user_type = 'teacher'

    filter_by_score = (
        ("any", _("All")),  # Default
        ("no", _("Without score")),
        ("yes", _("With grade")),
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
                  "score",
                  "first_student_comment_at",
                  "student__first_name",
                  "student__last_name",
                  "assignment__id",
                  "assignment__course_id",
                  "assignment__is_online",
                  "assignment__passing_score",
                  "assignment__maximum_score",)
            .prefetch_related("student__groups",)
            .order_by('student__last_name', 'student__first_name'))

    def get_context_data(self, **kwargs):
        context = {
            "filter_by_score": self.filter_by_score,
            "filter_by_comments": self.filter_by_comments
        }
        filters = self.prepare_queryset_filters(context)
        if "assignment" in filters:
            course_id = filters["assignment"].course_id
            # TODO: select `deleted` instead?
            # TODO: move to separated method and return set
            qs = (Enrollment.active
                  .filter(course_id=course_id)
                  .values_list("student_id", flat=True))
            context["enrollments"] = set(qs)
        context["student_assignment_list"] = self.get_queryset(filters)
        # Url for assignment filter
        query_tuple = [
            ('term', self.query["term"]),
            ('course', self.query["course_slug"]),
            ('score', self.query["score"]),
            ('comment', self.query["comment"]),
            ('assignment', ""),  # should be the last one
        ]
        self.query["form_url"] = "{}?{}".format(
            reverse("teaching:assignment_list"),
            urlencode(OrderedDict(query_tuple))
        )
        context["query"] = self.query
        return context

    def prepare_queryset_filters(self, context):
        """
        We process GET-query in optimistic way - assume that invalid data 
        comes very rarely.
        Processing order of GET-params:
            term -> course -> assignment -> score -> comment
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
        8. Set filters by resulting assignment, score and last comment.
        """
        filters = {}
        teacher_all_courses = self._get_all_teacher_courses()
        all_terms = set(c.semester for c in teacher_all_courses)
        all_terms = sorted(all_terms, key=lambda t: -t.index)
        # Try to get course offerings for requested term
        query_term_index = self._get_requested_term_index(all_terms)
        course_offerings = [c for c in teacher_all_courses
                            if c.semester.index == query_term_index]
        # Try to get assignments for requested course
        query_co = self._get_requested_course(course_offerings)
        # FIXME: attach course or pass it to deadline_at_local
        assignments = list(
            Assignment.objects
            .filter(notify_teachers__teacher=self.request.user,
                    course=query_co)
            .only("pk", "deadline_at", "title", "course_id")
            .order_by("-deadline_at"))
        query_assignment = self._get_requested_assignment(assignments)
        if query_assignment:
            filters["assignment"] = query_assignment
        # Set filter by score
        query_score, filter_name, filter_value = self._get_filter_by_score()
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
            "score": query_score,
            "comment": query_comment
        }
        return filters

    def _get_filter_by_score(self):
        filter_name, filter_value = None, None
        query_value = self.request.GET.get("score", "any")
        # FIXME: validate GET-params in separated method? and redirect?
        if query_value not in (k for k, v in self.filter_by_score):
            query_value = "any"
        if query_value == "no":
            filter_name, filter_value = "score__isnull", True
        elif query_value == "yes":
            filter_name, filter_value = "score__isnull", False
        # FIXME: Может не устанавливать его вообще :<
        return query_value, filter_name, filter_value

    def _get_filter_by_status(self):
        filter_name, filter_value = None, None
        query_value = self.request.GET.get("comment", "any")
        if query_value not in (k for k, v in self.filter_by_comments):
            query_value = "any"
        if query_value == "student":
            filter_name = "last_comment_from"
            filter_value = self.model.CommentAuthorTypes.STUDENT
        elif query_value == "teacher":
            filter_name = "last_comment_from"
            filter_value = self.model.CommentAuthorTypes.TEACHER
        elif query_value == "empty":
            filter_name = "last_comment_from"
            filter_value = self.model.CommentAuthorTypes.NOBODY
        return query_value, filter_name, filter_value

    def _get_all_teacher_courses(self):
        """Returns all courses for authenticated teacher"""
        u = self.request.user
        cs = (Course.objects
              .filter(teachers=u)
              .select_related("meta_course", "semester")
              .order_by("semester__index", "meta_course__name"))
        if not cs:
            logger.warning(f"Teacher {u} has not conducted any course")
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
            if term_type not in SemesterTypes.values:
                raise ValidationError("Wrong term type")
            term = next((t for t in all_terms if
                         t.type == term_type and t.year == year), None)
            if not term:
                raise ValidationError("Term not presented among available")
        except (ValueError, ValidationError):
            raise Redirect(to=reverse("teaching:assignment_list"))
        return term.index

    def _get_requested_course(self, courses):
        assert len(courses) > 0
        """Get requested course by GET-param `course`"""
        course_slug = self.request.GET.get("course", "")
        try:
            co = next(c for c in courses if c.meta_course.slug == course_slug)
        except StopIteration:
            # TODO: get term and redirect to entry page
            co = courses[0]
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
        raise Redirect(to=reverse("teaching:course_list"))


class AssignmentTeacherDetailView(TeacherOnlyMixin,
                                  generic.DetailView):
    model = Assignment
    template_name = "learning/teaching/assignment_detail.html"
    context_object_name = 'assignment'

    def get_queryset(self):
        return (Assignment.objects
                .select_related('course',
                                'course__meta_course',
                                'course__semester')
                .prefetch_related('assignmentattachment_set'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = course_access_role(course=self.object.course,
                                  user=self.request.user)
        if role not in [CourseRole.CURATOR, CourseRole.TEACHER]:
            raise PermissionDenied
        context['a_s_list'] = (
            StudentAssignment.objects
            .filter(assignment__pk=self.object.pk)
            .select_related('assignment',
                            'assignment__course',
                            'assignment__course__meta_course',
                            'assignment__course__semester',
                            'student')
            .prefetch_related('student__groups'))
        return context


class AssignmentProgressBaseView(AccessMixin):
    model = AssignmentComment
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
                                'assignment__course',
                                'assignment__course__meta_course',
                                'assignment__course__semester')
                .first())

    @staticmethod
    def _prefetch_data(student_assignment):
        prefetch_comments = Prefetch('assignmentcomment_set',
                                     queryset=(AssignmentComment.objects
                                               .select_related('author')
                                               .order_by('created')))
        prefetch_related_objects([student_assignment],
                                 prefetch_comments,
                                 'assignment__course__teachers',
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
        co = sa.assignment.course
        tz_override = co.get_city_timezone()
        # For online courses format datetime in student timezone
        # Note, that this view available for teachers, curators and
        # enrolled students only
        if co.is_correspondence and (user.is_student or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_id]
        context = {
            'user_type': self.user_type,
            'a_s': sa,
            'form': form,
            'timezone': tz_override,
            'first_comment_after_deadline': first_comment_after_deadline,
            'one_teacher': sa.assignment.course.teachers.count() == 1,
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
    template_name = "learning/assignment_submission_detail.html"

    # FIXME: combine has_permissions_*
    def has_permissions_coarse(self, user):
        return user.is_curator or user.is_teacher

    def has_permissions_precise(self, user):
        co = self.student_assignment.assignment.course
        role = course_access_role(course=co, user=user)
        return role in [CourseRole.TEACHER, CourseRole.CURATOR]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        a_s = self.student_assignment
        co = a_s.assignment.course
        # Get next unchecked assignment
        base = (StudentAssignment.objects
                .filter(score__isnull=True,
                        first_student_comment_at__isnull=False,
                        assignment__course=co,
                        assignment__course__teachers=self.request.user)
                .order_by('assignment__deadline_at', 'pk')
                .only('pk'))
        next_a_s = (base.filter(pk__gt=a_s.pk).first() or
                    base.filter(pk__lt=a_s.pk).first())
        context['next_a_s_pk'] = next_a_s.pk if next_a_s else None
        context['is_actual_teacher'] = self.request.user in co.teachers.all()
        context['score_form'] = AssignmentScoreForm(
            initial={'score': a_s.score},
            maximum_score=a_s.assignment.maximum_score)
        return context

    def post(self, request, *args, **kwargs):
        # TODO: separate to update view
        if 'grading_form' in request.POST:
            a_s = self.student_assignment
            form = AssignmentScoreForm(request.POST,
                                       maximum_score=a_s.assignment.maximum_score)

            # Too hard to use ProtectedFormMixin here, let's just inline it's
            # logic. A little drawback is that teachers still can leave
            # comments under other's teachers assignments, but can not grade,
            # so it's acceptable, IMO.
            teachers = a_s.assignment.course.teachers.all()
            if request.user not in teachers:
                raise PermissionDenied

            if form.is_valid():
                a_s.score = form.cleaned_data['score']
                a_s.save()
                if a_s.score is None:
                    messages.info(self.request,
                                  _("Score was deleted"),
                                  extra_tags='timeout')
                else:
                    messages.success(self.request,
                                     _("Score successfully saved"),
                                     extra_tags='timeout')
                return redirect(a_s.get_teacher_url())
            else:
                # not sure if we can do anything more meaningful here.
                # it shouldn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(form.errors))
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.student_assignment.get_teacher_url()


class AssignmentCommentAttachmentDownloadView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
            if attachment_type != ASSIGNMENT_COMMENT_ATTACHMENT:
                return HttpResponseBadRequest()
        except IndexError:
            raise Http404

        response = HttpResponse()
        user = request.user
        qs = AssignmentComment.objects.filter(pk=pk)
        if not user.is_teacher and not user.is_curator:
            qs = qs.filter(student_assignment__student_id=user.pk)
        # TODO: restrict access for teachers
        comment = get_object_or_404(qs)
        file_field = comment.attached_file
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
                    html_exporter = HTMLExporter()
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


class EventDetailView(generic.DetailView):
    model = Event
    context_object_name = 'event'
    template_name = "learning/event_detail.html"


# FIXME: -> courses app
class AssignmentAttachmentDownloadView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
        except IndexError:
            raise Http404

        if attachment_type != ASSIGNMENT_TASK_ATTACHMENT:
            return HttpResponseBadRequest()
        file_field = self.get_task_attachment(pk)
        if file_field is None:
            return HttpResponseForbidden()

        response = HttpResponse()
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
                    html_exporter = HTMLExporter()
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
              .select_related("assignment", "assignment__course"))
        assignment_attachment = get_object_or_404(qs)
        role = course_access_role(course=assignment_attachment.assignment.course,
                                  user=self.request.user)
        # User doesn't have private access to the task
        if role != CourseRole.NO_ROLE and role != CourseRole.STUDENT_RESTRICT:
            return assignment_attachment.attachment
        return None
