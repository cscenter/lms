import csv
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
from django.db.models import FileField, F
from django.http import FileResponse, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic.edit import BaseUpdateView

from auth.mixins import PermissionRequiredMixin
from code_reviews.gerrit.constants import GerritRobotMessages
from core import comment_persistence
from core.api.fields import CharSeparatedField
from core.exceptions import Redirect
from core.http import HttpRequest
from core.urls import reverse
from core.utils import bucketize, render_markdown
from courses.constants import AssignmentStatus, AssignmentFormat
from courses.models import Assignment, Course, CourseTeacher
from courses.permissions import DeleteAssignment, EditAssignment, ViewAssignment
from courses.selectors import (
    assignments_list, course_teachers_prefetch_queryset, get_course_teachers
)
from courses.services import CourseService
from grading.api.yandex_contest import SubmissionVerdict
from grading.constants import SubmissionStatus
from learning.forms import AssignmentModalCommentForm, AssignmentReviewForm
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment, StudentAssignment
)
from learning.permissions import (
    CreateAssignmentComment, DownloadAssignmentSolutions, EditStudentAssignment,
    ViewStudentAssignment, ViewStudentAssignmentList, ViewOwnStudentAssignment
)
from learning.selectors import get_enrollment, get_teacher_not_spectator_courses
from learning.services import AssignmentService, StudentGroupService
from learning.services.personal_assignment_service import (
    create_personal_assignment_review, get_assignment_update_history_message,
    get_draft_comment
)
from learning.settings import AssignmentScoreUpdateSource
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
    types_for_select = [AssignmentFormat.ONLINE, AssignmentFormat.CODE_REVIEW]
    for i, assignment in enumerate(assignments_queryset):
        is_selected = assignment.submission_type in types_for_select
        assignments.append({
            "value": assignment.pk,
            "label": assignment.title,
            "selected": str(assignment.pk) in assignments_filter if assignments_filter else is_selected
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
                    "courseGroups": filters["courseGroups"],
                    "statusOptions": [{'value': v, 'label': str(l)} for v, l in AssignmentStatus.choices
                                      if v != AssignmentStatus.NEW]
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
        context["can_download_status_report"] = self.object.submission_type in [AssignmentFormat.ONLINE,
                                                                                AssignmentFormat.CODE_REVIEW]
        context["can_download_answers_csv"] = self.object.submission_type in [AssignmentFormat.ONLINE,
                                                                                AssignmentFormat.CODE_REVIEW]
        context['status_report_href'] = reverse('teaching:assignment_status_log_csv', kwargs={'pk': self.object.pk})
        return context


class AssignmentStatusLogCSVView(PermissionRequiredMixin, generic.DetailView):
    model = Assignment
    permission_required = ViewAssignment.name

    def get_permission_object(self):
        return self.get_object().course

    def get(self, request, *args, **kwargs):
        assignment = self.get_object()
        if assignment.submission_type not in [AssignmentFormat.ONLINE, AssignmentFormat.CODE_REVIEW]:
            return HttpResponseBadRequest()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f"{datetime.date.today()}-status-changes_pk-{assignment.pk}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        headers = [
            "student",
            "student_id",
            "task",
            "comment_author",
            "comment_author_id",
            "action",
            "comment_posted_ISO"
        ]
        writer.writerow(headers)
        comments = (AssignmentComment.objects
                    .filter(is_published=True,
                            student_assignment__assignment=assignment)
                    .select_related('author',
                                    'submission',
                                    'student_assignment__student')
                    .order_by('student_assignment__student', 'created'))
        for comment in comments:
            title = assignment.title
            student = comment.student_assignment.student
            comment_author = comment.author
            created = comment.created.isoformat()
            action_text = None
            if not isinstance(comment.meta, dict) or \
                'status' not in comment.meta or 'status_old' not in comment.meta:
                continue
            is_comment_from_student = comment_author == student
            is_publish_online_solution = is_comment_from_student and \
                                         assignment.submission_type == AssignmentFormat.ONLINE and \
                                         comment.meta['status'] == AssignmentStatus.ON_CHECKING
            is_publish_review_solution = assignment.submission_type == AssignmentFormat.CODE_REVIEW and \
                                         comment.type == AssignmentSubmissionTypes.SOLUTION and \
                                         comment.submission.status == SubmissionStatus.PASSED and \
                                         comment.submission.verdict_or_status == SubmissionVerdict.OK.value
            is_status_changed_on_needfixes = comment.meta['status'] != comment.meta['status_old'] and \
                                             comment.meta['status'] == AssignmentStatus.NEED_FIXES
            is_status_changed_on_completed = comment.meta['status'] != comment.meta['status_old'] and \
                                             comment.meta['status'] == AssignmentStatus.COMPLETED
            if is_status_changed_on_completed:
                action_text = 'оценка обновлена'
            elif is_publish_online_solution or is_publish_review_solution:
                action_text = 'решение отправлено на проверку'
            elif is_status_changed_on_needfixes:
                action_text = 'получен комментарий от ревьювера'
            if action_text is not None:
                writer.writerow([student.get_short_name(), student.pk, title,
                                 comment_author.get_short_name(), comment_author.pk,
                                 action_text, created])
        return response

class AssignmentStudentAnswersCSVView(PermissionRequiredMixin, generic.DetailView):
    model = Assignment
    permission_required = ViewAssignment.name

    def get_permission_object(self):
        return self.get_object().course

    def get(self, request, *args, **kwargs):
        assignment = self.get_object()
        if assignment.submission_type not in [AssignmentFormat.ONLINE, AssignmentFormat.CODE_REVIEW]:
            return HttpResponseBadRequest()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f"{datetime.date.today()}-students_answers-{assignment.pk}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        headers = [
            "Профиль на сайте",
            "Фамилия",
            "Имя",
            "Отчество",
            "Отделение",
            "Текстовый ответ"
        ]
        writer.writerow(headers)
        comments = (AssignmentComment.objects
                    .filter(is_published=True,
                            student_assignment__assignment=assignment,
                            author=F('student_assignment__student'))
                    .select_related('author__branch')
                    .order_by('student_assignment__student', 'created'))
        for comment in comments:
            student = comment.author
            writer.writerow([student.get_absolute_url(), student.last_name, student.first_name, student.patronymic,
                             value.name if (value := student.branch) else "Не выставлено",
                             value if (value := comment.text) else "-",
                             ])
        return response


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "lms/teaching/student_assignment_detail.html"
    permission_required = ViewStudentAssignment.name

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.has_permission():
            has_student_permission = request.user.has_perm(ViewOwnStudentAssignment.name,
                                                           self.student_assignment)
            if has_student_permission and request.method == "GET":
                return redirect(self.student_assignment.get_student_url())
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
                                 meta__stats__has_key='solutions',
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

    def post(self, request, *args, **kwargs):
        sa = self.student_assignment
        if not request.user.has_perm(EditStudentAssignment.name, sa):
            raise PermissionDenied
        form = AssignmentReviewForm(data=request.POST,
                                    files=request.FILES,
                                    student_assignment=sa)
        if form.is_valid():
            is_draft = "save-draft" in self.request.POST
            try:
                with transaction.atomic():
                    create_personal_assignment_review(
                        student_assignment=sa,
                        reviewer=self.request.user,
                        is_draft=is_draft,
                        score_old=form.cleaned_data['score_old'],
                        score_new=form.cleaned_data['score'],
                        status_old=form.cleaned_data['status_old'],
                        status_new=form.cleaned_data['status'],
                        source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT,
                        message=form.cleaned_data['text'],
                        attachment=form.cleaned_data['attached_file'])
                if form.cleaned_data['text']:
                    comment_persistence.add_to_gc(form.cleaned_data['text'])
                message = "Данные успешно сохранены"
                messages.success(self.request, message=message, extra_tags='timeout')
                return redirect(sa.get_teacher_url())
            except ValidationError as e:
                message = str(e.args[0] if e.args else e)
                messages.error(self.request, message=message, extra_tags='timeout')
        return self.form_invalid(form)

    def form_invalid(self, form: AssignmentReviewForm):
        msg = "<br>".join("<br>".join(errors) for errors in form.errors.values())
        messages.error(self.request, "Данные не сохранены!<br>" + msg, extra_tags="timeout")
        context = self.get_context_data()
        # In case of a failed concurrent update renew form data with an actual
        # DB values.
        self.student_assignment.refresh_from_db()
        form_data = form.data.copy()
        sa = self.student_assignment
        form_data['review-score'] = sa.score
        form_data['review-score_old'] = sa.score
        form_data['review-status'] = sa.status
        form_data['review-status_old'] = sa.status
        form.data = form_data
        context['review_form'] = form
        return self.render_to_response(context)


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
