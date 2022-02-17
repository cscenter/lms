import datetime
import os.path
import tempfile
import zipfile
from typing import Any, Dict, Iterator, List, NamedTuple

from rest_framework import serializers
from vanilla import TemplateView

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import FileField
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic.edit import BaseUpdateView

from auth.mixins import PermissionRequiredMixin
from core import comment_persistence
from core.api.fields import CharSeparatedField
from core.exceptions import Redirect
from core.http import HttpRequest
from core.urls import reverse
from core.utils import bucketize, render_markdown
from courses.constants import AssignmentStatuses
from courses.models import Assignment, Course, CourseTeacher
from courses.permissions import DeleteAssignment, EditAssignment, ViewAssignment
from courses.selectors import (
    assignments_list, course_teachers_prefetch_queryset, get_course_teachers
)
from courses.services import CourseService
from learning.forms import AssignmentModalCommentForm, AssignmentReviewForm
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment, StudentAssignment
)
from learning.permissions import (
    CreateAssignmentComment, DownloadAssignmentSolutions, EditStudentAssignment,
    ViewStudentAssignment, ViewStudentAssignmentList
)
from learning.selectors import get_enrollment, get_teacher_not_spectator_courses
from learning.services import AssignmentService, StudentGroupService
from learning.services.personal_assignment_service import (
    create_personal_assignment_review, get_assignment_update_history_message,
    get_draft_comment
)
from learning.utils import humanize_duration
from learning.views import AssignmentCommentUpsertView, AssignmentSubmissionBaseView


def _check_queue_filters(course: Course, query_params):
    """
    Returns filter options for the selected course in the assignments
    check queue.
    """
    assignments = []
    assignments_filter = query_params.get('assignments', {})
    assignments_queryset = assignments_list(filters={"course": course}).order_by('-deadline_at', 'title')
    for i, assignment in enumerate(assignments_queryset):
        assignments.append({
            "value": assignment.pk,
            "label": assignment.title,
            "selected": str(assignment.pk) in assignments_filter if assignments_filter else i < 2
        })
    # Course teachers
    course_teachers = [{"value": "unset", "label": "Не назначен", "selected": False}]
    teachers_qs = (course_teachers_prefetch_queryset(role_priority=False,
                                                     hidden_roles=(CourseTeacher.roles.spectator,))
                   .filter(course=course))
    for course_teacher in teachers_qs:
        value = course_teacher.pk
        label = course_teacher.teacher.get_short_name(last_name_first=True)
        course_teachers.append({"value": value, "label": label, "selected": False})
    # Student groups
    student_groups_ = CourseService.get_student_groups(course)
    sites_total = StudentGroupService.unique_sites(student_groups_)
    student_groups = []
    for g in student_groups_:
        label = g.get_name(branch_details=sites_total > 1)
        student_groups.append({"value": g.pk, "label": label, "selected": False})
    return {
        "assignments": assignments,
        "courseTeachers": course_teachers,
        "courseGroups": student_groups
    }


class AssignmentCheckQueueView(PermissionRequiredMixin, TemplateView):
    permission_required = ViewStudentAssignmentList.name
    template_name = "lms/teaching/assignments_check_queue.html"

    class InputSerializer(serializers.Serializer):
        course = serializers.ChoiceField(choices=(), allow_blank=False,
                                         required=False)
        assignments = CharSeparatedField(label="Assignments",
                                         allow_blank=True,
                                         required=False)

        def __init__(self, courses: List[Course], **kwargs):
            super().__init__(**kwargs)
            self.fields['course'].choices = [(c.pk, c.name) for c in courses]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        teacher = self.request.user
        courses = list(get_teacher_not_spectator_courses(teacher)
                       .filter(main_branch__site=self.request.site)
                       .order_by("-semester__index", "meta_course__name"))
        if not courses:
            return {}
        serializer = self.InputSerializer(courses, data=self.request.GET)
        if not serializer.is_valid(raise_exception=False):
            # Use defaults and redirect
            raise Redirect(to=self.request.path_info)
        # Course options
        course_options = []
        # Group courses by meta course inside each semester
        grouped_courses = bucketize(courses, key=lambda c: (c.semester_id, c.meta_course_id))
        for semester, semester_courses in grouped_courses.items():
            for course in semester_courses:
                course_name = f"{course.name}, {course.semester.name}"
                if len(semester_courses) > 1:
                    course_name += f" {course.main_branch.name}"
                course_options.append({
                    "value": course.pk,
                    "label": course_name
                })
        # Selected course
        course_id = serializer.validated_data.get('course') or courses[0].pk
        course = next((c for c in courses if c.pk == course_id))
        filters = _check_queue_filters(course, serializer.validated_data)
        return {
            "app_data": {
                "props": {
                    "timeZone": str(self.request.user.time_zone),
                    "csrfToken": get_token(self.request),
                    "courseOptions": course_options,
                    "courseTeachers": filters["courseTeachers"],
                    "courseGroups": filters["courseGroups"]
                },
                "state": {
                    "course": course.pk,
                    "selectedAssignments": [a["value"] for a in filters['assignments']
                                            if a["selected"]]
                }
            }
        }


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
            if comment.is_stale_for_edit:
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
    template_name = "lms/teaching/assignment_detail.html"
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
        context["can_edit_assignment"] = self.request.user.has_perm(EditAssignment.name, self.object)
        context["can_delete_assignment"] = self.request.user.has_perm(DeleteAssignment.name, self.object)
        return context


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "lms/teaching/student_assignment_detail.html"
    permission_required = ViewStudentAssignment.name

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.has_permission():
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.student_assignment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        sa = self.student_assignment
        course = sa.assignment.course
        # FIXME: переписать с union + first, перенести в manager
        ungraded_base = (StudentAssignment.objects
                         .filter(score__isnull=True,
                                 first_student_comment_at__isnull=False,
                                 assignment__course=course,
                                 assignment__course__teachers=user,
                                 assignment__course__course_teachers__roles=~CourseTeacher.roles.spectator)
                         .order_by('assignment__deadline_at', 'pk')
                         .only('pk'))
        next_ungraded = (ungraded_base.filter(pk__gt=sa.pk).first() or
                         ungraded_base.filter(pk__lt=sa.pk).first())
        context['next_student_assignment'] = next_ungraded
        context['is_actual_teacher'] = course.is_actual_teacher(user.pk)
        enrollment = get_enrollment(course=course, student=sa.student)
        context['student_course_progress_url'] = reverse('teaching:student-progress', kwargs={
            "enrollment_id": enrollment.pk,
            **course.url_kwargs
        })
        context['assignee_teachers'] = get_course_teachers(course=course)
        context['max_score'] = str(sa.assignment.maximum_score)
        context['review_form'] = AssignmentReviewForm(student_assignment=sa,
                                                       draft_comment=get_draft_comment(user, sa))
        # Some estimates on showing audit log link or not.
        context['show_score_audit_log'] = (sa.score is not None or
                                           sa.score_changed - sa.created > datetime.timedelta(seconds=2))
        context['can_edit_score'] = self.request.user.has_perm(EditStudentAssignment.name, sa)
        context['get_score_status_changing_message'] = get_assignment_update_history_message
        return context

    def form_invalid(self, form):
        msg = "<br>".join("<br>".join(errors)
                          for errors in form.errors.values())
        messages.error(self.request, "Данные не сохранены!<br>" + msg, extra_tags="timeout")
        context = self.get_context_data()
        self.student_assignment.refresh_from_db()
        sa = self.student_assignment
        form_data = self.request.POST.copy()
        form_data['review-score'] = sa.score
        form_data['review-status'] = sa.status
        form_data['review-score_old'] = sa.score
        form_data['review-old_status'] = sa.status
        new_form = AssignmentReviewForm(data=form_data,
                                        student_assignment=sa)
        for field, errors in form.errors.items():
            for error in errors:
                if error not in new_form.errors.get(field, []):
                    new_form.add_error(field, error)
        context['review_form'] = new_form
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        sa = self.student_assignment
        if not request.user.has_perm(EditStudentAssignment.name, sa):
            raise PermissionDenied
        form = AssignmentReviewForm(data=request.POST,
                                    files=request.FILES,
                                    student_assignment=sa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    is_draft = "save-draft" in self.request.POST
                    create_personal_assignment_review(
                        student_assignment=sa,
                        reviewer=self.request.user,
                        is_draft=is_draft,
                        score_old=form.cleaned_data['score_old'],
                        score_new=form.cleaned_data['score'],
                        old_status=form.cleaned_data['old_status'],
                        new_status=form.cleaned_data['status'],
                        message=form.cleaned_data['text'],
                        attachment=form.cleaned_data['attached_file'],
                    )
                    if form.cleaned_data['text']:
                        comment_persistence.add_to_gc(form.cleaned_data['text'])
                return redirect(sa.get_teacher_url())
            except ValidationError as e:
                message = str(e.args[0] if e.args else e)
                messages.error(self.request, message=message, extra_tags='timeout')
        return self.form_invalid(form)


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = CreateAssignmentComment.name

    def get_permission_object(self):
        return self.student_assignment

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
