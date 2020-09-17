import datetime
import logging
from typing import Optional

from django.contrib import messages
from django.db.models import Prefetch
from django.http import Http404, JsonResponse, \
    HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import generic
from vanilla import TemplateView, GenericModelView

from core import comment_persistence
from core.utils import hashids
from core.views import LoginRequiredMixin
from courses.models import AssignmentAttachment
from courses.views.mixins import CourseURLParamsMixin
from files.views import ProtectedFileDownloadView
from learning.forms import AssignmentCommentForm
from learning.models import StudentAssignment, AssignmentComment, \
    AssignmentNotification, Event, CourseNewsNotification, \
    AssignmentSubmissionTypes
from learning.permissions import ViewAssignmentCommentAttachment, \
    ViewAssignmentAttachment
from learning.study.services import get_draft_comment, get_draft_submission
from users.mixins import TeacherOnlyMixin

logger = logging.getLogger(__name__)


__all__ = (
    'AssignmentSubmissionBaseView', 'EventDetailView',
    'AssignmentAttachmentDownloadView', 'CourseNewsNotificationUpdate',
    'CourseStudentsView', 'AssignmentCommentAttachmentDownloadView',
)


class StudentAssignmentURLParamsMixin:
    """
    Fetches student assignment by URL params and attaches it to the view kwargs.
    """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.student_assignment: StudentAssignment = get_object_or_404(
            self.get_student_assignment_queryset())

    def get_student_assignment_queryset(self):
        return (StudentAssignment.objects
                .filter(pk=self.kwargs['pk'])
                .select_related('student',
                                'assignment',
                                'assignment__course',
                                'assignment__course__main_branch',
                                'assignment__course__meta_course',
                                'assignment__course__semester'))


class AssignmentCommentUpsertView(StudentAssignmentURLParamsMixin,
                                  GenericModelView):
    """Post a new comment or save draft"""
    model = AssignmentComment
    submission_type = None

    def post(self, request, *args, **kwargs):
        # Saving drafts is only supported for comments.
        is_comment = (self.submission_type == AssignmentSubmissionTypes.COMMENT)
        save_draft = is_comment and "save-draft" in request.POST
        assert self.submission_type is not None
        submission = get_draft_submission(request.user,
                                          self.student_assignment,
                                          self.submission_type,
                                          build=True)
        submission.is_published = not save_draft
        form = self.get_form(data=request.POST, files=request.FILES,
                             instance=submission)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.student_assignment = self.student_assignment
        comment.author = self.request.user
        comment.save()
        comment_persistence.report_saved(comment.text)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        msg = "<br>".join("<br>".join(errors) for errors in
                          form.errors.values())
        messages.error(self.request, "Данные не сохранены!<br>" + msg)
        redirect_to = self.get_error_url()
        return HttpResponseRedirect(redirect_to)

    def get_error_url(self):
        raise NotImplementedError


class AssignmentSubmissionBaseView(StudentAssignmentURLParamsMixin,
                                   TemplateView):

    def get_student_assignment_queryset(self):
        qs = super().get_student_assignment_queryset()
        prefetch_comments = Prefetch('assignmentcomment_set',
                                     queryset=(AssignmentComment.published
                                               .select_related('author')
                                               .order_by('created')))
        return qs.prefetch_related(prefetch_comments,
                                   'assignment__course__teachers',
                                   'assignment__assignmentattachment_set')

    def get_context_data(self, **kwargs):
        sa = self.student_assignment
        user = self.request.user
        # Not sure if it's the best place for this, but it's the simplest one
        (AssignmentNotification.unread
         .filter(student_assignment=sa, user=user)
         .update(is_unread=False))
        # TODO: move to the StudentAssignment model?
        # Let's consider the last minute of the deadline in favor of the student
        deadline_at = sa.assignment.deadline_at + datetime.timedelta(minutes=1)
        cs_after_deadline = (c for c in sa.assignmentcomment_set.all() if
                             c.created >= deadline_at)
        first_comment_after_deadline = next(cs_after_deadline, None)
        draft_comment = get_draft_comment(user, self.student_assignment)
        comment_form = AssignmentCommentForm(instance=draft_comment)
        context = {
            'a_s': sa,
            'timezone': sa.assignment.course.get_timezone(),
            'first_comment_after_deadline': first_comment_after_deadline,
            'one_teacher': sa.assignment.course.teachers.count() == 1,
            'hashes_json': comment_persistence.get_hashes_json(),
            'comment_form': comment_form,
        }
        return context


class EventDetailView(generic.DetailView):
    model = Event
    context_object_name = 'event'
    template_name = "learning/event_detail.html"


class AssignmentAttachmentDownloadView(ProtectedFileDownloadView):
    permission_required = ViewAssignmentAttachment.name
    file_field_name = 'attachment'

    def get_protected_object(self) -> Optional[AssignmentAttachment]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (AssignmentAttachment.objects
              .filter(pk=ids[0])
              .select_related("assignment__course"))
        return get_object_or_404(qs)

    def get_permission_object(self):
        return self.protected_object.assignment


class AssignmentCommentAttachmentDownloadView(ProtectedFileDownloadView):
    permission_required = ViewAssignmentCommentAttachment.name
    file_field_name = 'attached_file'

    def get_protected_object(self) -> Optional[AssignmentComment]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (AssignmentComment.published
              .filter(pk=ids[0])
              .select_related("student_assignment__assignment__course"))
        return get_object_or_404(qs)

    def get_permission_object(self):
        return self.protected_object.student_assignment


class CourseNewsNotificationUpdate(LoginRequiredMixin, CourseURLParamsMixin,
                                   generic.View):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        updated = (CourseNewsNotification.unread
                   .filter(course_offering_news__course=self.course,
                           user_id=self.request.user.pk)
                   .update(is_unread=False))
        return JsonResponse({"updated": bool(updated)})


class CourseStudentsView(TeacherOnlyMixin, CourseURLParamsMixin, TemplateView):
    # raise_exception = True
    template_name = "learning/course_students.html"

    def handle_no_permission(self, request):
        raise Http404

    def get_context_data(self, **kwargs):
        course = self.course
        return {
            "course": course,
            "enrollments": (course.enrollment_set(manager="active")
                            .select_related("student", "student_profile"))
        }
