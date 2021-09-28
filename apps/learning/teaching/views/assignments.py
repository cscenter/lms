import os.path
import tempfile
import zipfile
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, NamedTuple
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django_filters.views import FilterMixin
from rest_framework import serializers
from vanilla import TemplateView

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import FileField
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic.edit import BaseUpdateView

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.urls import reverse
from core.utils import bucketize, render_markdown
from courses.constants import SemesterTypes
from courses.models import Assignment, Course, CourseTeacher
from courses.permissions import ViewAssignment
from learning.api.serializers import AssignmentScoreSerializer
from learning.forms import (
    AssignmentCommentForm, AssignmentModalCommentForm, AssignmentScoreForm
)
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment, StudentAssignment
)
from learning.permissions import (
    CreateAssignmentComment, DownloadAssignmentSolutions, EditOwnStudentAssignment,
    ViewStudentAssignment, ViewStudentAssignmentList
)
from learning.selectors import (
    get_active_enrollments, get_course_assignments, get_teacher_courses
)
from learning.services import AssignmentService
from learning.teaching.filters import AssignmentStudentsFilter
from learning.utils import humanize_duration
from learning.views import AssignmentCommentUpsertView, AssignmentSubmissionBaseView


class AssignmentCheckQueueView(PermissionRequiredMixin, TemplateView):
    permission_required = ViewStudentAssignmentList.name
    template_name = "lms/teaching/assignments_check_queue.html"

    class InputSerializer(serializers.Serializer):
        course = serializers.ChoiceField(choices=(), allow_blank=False,
                                         required=False)
        assignments = serializers.ListField(
            label="Assignments",
            child=serializers.IntegerField(min_value=1),
            min_length=1,
            allow_empty=False,
            required=False)

        def __init__(self, courses: List[Course], **kwargs):
            super().__init__(**kwargs)
            self.fields['course'].choices = [(c.pk, c.name) for c in courses]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        teacher = self.request.user
        courses = list(get_teacher_courses(teacher)
                       .order_by("-semester__index", "meta_course__name"))
        if not courses:
            return {}
        serializer = self.InputSerializer(courses, data=self.request.GET)
        if not serializer.is_valid(raise_exception=False):
            # Use defaults and redirect
            raise Redirect(to=self.request.path_info)
        # Group courses by meta course inside each semester
        by_semester = bucketize(courses, key=lambda c: (c.semester_id, c.meta_course_id))
        # Get assignments for the selected course
        course_id = serializer.validated_data.get('course') or courses[0].pk
        course = next((c for c in courses if c.pk == course_id))
        # TODO: убедиться, что среди указанных assignments есть валидные значения, но в какой момент?
        return {
            "options": {
                "courses": by_semester,
                # TODO: сортировать по дедлайну
                "assignments": get_course_assignments(course),
                # TODO: брать список всех проверяющих из настроек курса + список студенческих групп
            },
            "state": {
                "course": course,
            },
        }


def set_query_parameter(url, param_name, param_value):
    """
    Given a URL, set or replace a query parameter and return the modified URL.
    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


# Note: Wow, looks like a shit
class AssignmentListView(PermissionRequiredMixin, FilterMixin, TemplateView):
    permission_required = ViewStudentAssignmentList.name
    filterset_class = AssignmentStudentsFilter
    model = StudentAssignment
    template_name = "learning/teaching/assignment_list.html"

    def get_queryset(self, filters):
        return (
            StudentAssignment.objects
            .filter(**filters)
            .select_related("assignment", "student",)
            .only("id",
                  "score",
                  "first_student_comment_at",
                  "student__username",
                  "student__first_name",
                  "student__last_name",
                  "student__gender",
                  "assignment__id",
                  "assignment__course_id",
                  "assignment__submission_type",
                  "assignment__passing_score",
                  "assignment__maximum_score",)
            .prefetch_related("student__groups",)
            .order_by('student__last_name', 'student__first_name'))

    def get_context_data(self, **kwargs):
        context = {}
        data = self.get_assignment_with_navigation_data()
        assignment, assignments, courses, terms = data
        filters = {}
        query_params = {}
        if assignment:
            course = assignment.course
            filters["assignment"] = assignment
            query_params["assignment"] = assignment.pk
            active_enrollments = (get_active_enrollments(assignment.course_id)
                                  .values_list("student_id", flat=True))
            context["enrollments"] = set(active_enrollments)
        else:
            course = courses[0]
        query_params["course"] = course.meta_course.slug
        query_params["term"] = course.semester.slug

        context["tz_override"] = self.request.user.time_zone
        context["assignment"] = assignment
        context["all_terms"] = terms
        context["course_offerings"] = courses
        context["assignments"] = assignments
        filterset_class = self.get_filterset_class()
        filterset_kwargs = {
            'data': self.request.GET or None,
            'request': self.request,
            'queryset': self.get_queryset(filters),
            'course': course,
        }
        filterset = filterset_class(**filterset_kwargs)
        if not filterset.is_bound or filterset.is_valid():
            student_assignment_list = filterset.qs
        else:
            student_assignment_list = filterset.queryset.none()
        if filterset.form.is_bound:
            query_params['student_group'] = filterset.form.cleaned_data['student_group'] or 'any'
            query_params['score'] = filterset.form.cleaned_data['score'] or 'any'
            query_params['comment'] = filterset.form.cleaned_data['comment'] or 'any'
        else:
            query_params['student_group'] = 'any'
            query_params['score'] = 'any'
            query_params['comment'] = 'any'
        # Url prefix for assignments select
        query_tuple = [
            ('term', query_params.get("term", "")),
            ('course', query_params.get("course", "")),
            ('score', query_params["score"]),
            ('comment', query_params["comment"]),
            ('assignment', ""),  # should be the last one
        ]
        context["form_url"] = "{}?{}".format(
            reverse("teaching:assignment_list"),
            urlencode(OrderedDict(query_tuple))
        )
        context["student_assignment_list"] = student_assignment_list
        context['filter_by_comments'] = filterset.form.fields['comment'].choices
        context['filter_by_score'] = filterset.form.fields['score'].choices
        context['filter_by_student_group'] = filterset.form.fields['student_group'].choices
        context["query"] = query_params
        context["base_url"] = "{}?{}".format(
            reverse("teaching:assignment_list"),
            urlencode(query_params))
        context["set_query_parameter"] = set_query_parameter
        return context

    def get_assignment_with_navigation_data(self):
        """
        Returns requested assignment and data needed for navigation:
            * courses in the term of the requested assignment
            * all available terms
            * other assignments of the related course

        Redirects to the start page if query value is invalid.
        """
        teacher = self.request.user
        courses = (get_teacher_courses(teacher)
                   .order_by("semester__index", "meta_course__name"))
        if not courses:
            messages.info(self.request,
                          _("You were redirected from Assignments due to "
                            "empty course list."),
                          extra_tags='timeout')
            raise Redirect(to=reverse("teaching:course_list"))
        terms = set(c.semester for c in courses)  # remove duplicates
        terms = sorted(terms, key=lambda t: -t.index)  # restore DESC order
        # Try to get course for the requested term
        query_term_index = self._get_requested_term_index(terms)
        courses_in_target_term = [c for c in courses
                                  if c.semester.index == query_term_index]
        # Try to get assignments for requested course
        course = self._get_requested_course(courses_in_target_term)
        assignments = list(Assignment.objects
                           .filter(course=course)
                           .only("pk", "deadline_at", "title", "course_id")
                           .order_by("-deadline_at"))
        # Get requested assignment
        try:
            assignment_id = int(self.request.GET.get("assignment", ""))
        except ValueError:
            # FIXME: Ищем ближайшее, где должен наступить дедлайн
            assignment_id = next((a.pk for a in assignments), False)
        assignment = next((a for a in assignments
                           if a.pk == assignment_id), None)
        return assignment, assignments, courses_in_target_term, terms

    def _get_requested_term_index(self, terms):
        """
        Calculate term index from `term` and `year` GET-params.
        If term index not presented in teachers term_list, redirect
        to the latest available valid term from this list.
        """
        assert len(terms) > 0
        query_term = self.request.GET.get("term")
        if not query_term:
            return terms[0].index  # Terms are in descending order
        try:
            year, term_type = query_term.split("-")
            year = int(year)
            if year < settings.ESTABLISHED:  # invalid GET-param value
                raise ValidationError("Wrong year value")
            if term_type not in SemesterTypes.values:
                raise ValidationError("Wrong term type")
            term = next((t for t in terms if
                         t.type == term_type and t.year == year), None)
            if not term:
                raise ValidationError("Term is not presented among available")
        except (ValueError, ValidationError):
            raise Redirect(to=reverse("teaching:assignment_list"))
        return term.index

    def _get_requested_course(self, courses):
        assert len(courses) > 0
        course_slug = self.request.GET.get("course", "")
        course = next((c for c in courses
                       if c.meta_course.slug == course_slug), None)
        if course is None:
            # TODO: get term and redirect to entry page
            course = courses[0]
        return course


# TODO: add permissions tests! Or perhaps anyone can look outside comments if I missed something :<
# FIXME: replace with vanilla view
class AssignmentCommentUpdateView(generic.UpdateView):
    model = AssignmentComment
    pk_url_kwarg = 'comment_pk'
    context_object_name = "comment"
    template_name = "learning/teaching/modal_update_assignment_comment.html"
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


class AssignmentDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Assignment
    template_name = "learning/teaching/assignment_detail.html"
    context_object_name = 'assignment'
    permission_required = ViewAssignment.name

    def get_permission_object(self):
        self.object = self.get_object()
        return self.object.course

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self):
        return (Assignment.objects
                .select_related('course',
                                'course__main_branch',
                                'course__meta_course',
                                'course__semester')
                .prefetch_related('assignmentattachment_set'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['a_s_list'] = (
            StudentAssignment.objects
            .filter(assignment__pk=self.object.pk)
            .select_related('assignment',
                            'assignment__course',
                            'assignment__course__meta_course',
                            'assignment__course__semester',
                            'student')
            .prefetch_related('student__groups')
            .order_by('student__last_name', 'student__first_name'))
        # Note: it's possible to return values instead and
        # making 1 db hit instead of 3
        exec_mean = AssignmentService.get_mean_execution_time(self.object)
        exec_median = AssignmentService.get_median_execution_time(self.object)
        context["execution_time_mean"] = humanize_duration(exec_mean)
        context["execution_time_median"] = humanize_duration(exec_median)
        return context


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "learning/teaching/student_assignment_detail.html"
    permission_required = ViewStudentAssignment.name

    def get_permission_object(self):
        return self.student_assignment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        a_s = self.student_assignment
        course = a_s.assignment.course
        # FIXME: переписать с union + first, перенести в manager
        ungraded_base = (StudentAssignment.objects
                         .filter(score__isnull=True,
                                 first_student_comment_at__isnull=False,
                                 assignment__course=course,
                                 assignment__course__teachers=user,
                                 assignment__course__course_teachers__roles=~CourseTeacher.roles.spectator)
                         .order_by('assignment__deadline_at', 'pk')
                         .only('pk'))
        next_ungraded = (ungraded_base.filter(pk__gt=a_s.pk).first() or
                         ungraded_base.filter(pk__lt=a_s.pk).first())
        context['next_student_assignment'] = next_ungraded
        context['is_actual_teacher'] = course.is_actual_teacher(user.pk)
        context['score_form'] = AssignmentScoreForm(
            initial={'score': a_s.score},
            maximum_score=a_s.assignment.maximum_score)
        context['comment_form'].helper.form_action = reverse(
            'teaching:assignment_comment_create',
            kwargs={'pk': a_s.pk})
        return context

    def post(self, request, *args, **kwargs):
        if 'grading_form' in request.POST:
            sa = self.student_assignment
            if not request.user.has_perm(EditOwnStudentAssignment.name, sa):
                raise PermissionDenied

            serializer = AssignmentScoreSerializer(data=request.POST,
                                                   instance=sa)
            if serializer.is_valid():
                serializer.save()
                if serializer.instance.score is None:
                    messages.info(self.request, _("Score was deleted"),
                                  extra_tags='timeout')
                else:
                    messages.success(self.request, _("Score successfully saved"),
                                     extra_tags='timeout')
                return redirect(sa.get_teacher_url())
            else:
                # not sure if we can do anything more meaningful here.
                # it shouldn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(serializer.errors))


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = CreateAssignmentComment.name
    submission_type = AssignmentSubmissionTypes.COMMENT

    def get_permission_object(self):
        return self.student_assignment

    def get_form_class(self):
        return AssignmentCommentForm

    def get_success_url(self):
        return self.student_assignment.get_teacher_url()

    def get_error_url(self):
        return self.student_assignment.get_teacher_url()


class SolutionAttachmentZipFile(NamedTuple):
    path: str
    file_field: FileField


def _solution_attachments(assignment: Assignment) -> Iterator[SolutionAttachmentZipFile]:
    enrollments = (Enrollment.active
                   .filter(course_id=assignment.course_id)
                   .prefetch_related('student_group'))
    student_groups = {e.student_id: e.student_group.get_name() for e in enrollments}
    active_students = student_groups.keys()
    personal_assignments = (StudentAssignment.objects
                            .filter(assignment=assignment,
                                    student__in=active_students)
                            .select_related('student'))
    root_name = f"{assignment.pk}-{assignment.title}"
    for student_assignment in personal_assignments:
        solutions = list(AssignmentComment.published
                         .filter(student_assignment=student_assignment,
                                 type=AssignmentSubmissionTypes.SOLUTION))
        if solutions:
            student_group = student_groups[student_assignment.student_id]
            dir_name = student_assignment.student.get_abbreviated_short_name()
            for solution in solutions:
                file_field = solution.attached_file
                file_name = os.path.basename(file_field.name)
                yield SolutionAttachmentZipFile(
                    path=f"{root_name}/{student_group}/{dir_name}/{file_name}",
                    file_field=file_field)


class AssignmentDownloadSolutionAttachmentsView(PermissionRequiredMixin, generic.View):
    permission_required = DownloadAssignmentSolutions.name

    def get(self, request, *args, **kwargs):
        assignment_id = kwargs['pk']
        assignment = get_object_or_404(Assignment.objects.filter(pk=assignment_id))
        files = _solution_attachments(assignment)

        in_memory_size = 1024 * 1024 * 25  # 25 mb
        temp_file = tempfile.SpooledTemporaryFile(max_size=in_memory_size)
        with zipfile.ZipFile(temp_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            for attachment in files:
                file_field = attachment.file_field
                try:
                    with file_field.storage.open(file_field.name) as f:
                        zip_file.writestr(attachment.path, f.read())
                except FileNotFoundError:
                    pass

        file_size = temp_file.tell()
        temp_file.seek(0)
        file_name = 'download.zip'

        response = FileResponse(temp_file, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        response['Content-Length'] = file_size
        return response
