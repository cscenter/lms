import datetime
import logging
from typing import Optional

from vanilla import GenericModelView, TemplateView

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import generic

from core import comment_persistence
from core.http import AuthenticatedHttpRequest
from core.utils import hashids
from core.views import LoginRequiredMixin
from courses.models import AssignmentAttachment
from courses.selectors import course_teachers_prefetch_queryset
from courses.views.mixins import CourseURLParamsMixin
from files.views import ProtectedFileDownloadView
from learning.forms import AssignmentCommentForm
from learning.models import (
    AssignmentComment, AssignmentNotification, CourseNewsNotification, Event,
    StudentAssignment, SubmissionAttachment
)
from learning.permissions import (
    ViewAssignmentAttachment, ViewAssignmentCommentAttachment
)
from learning.services.personal_assignment_service import create_assignment_comment
from users.mixins import TeacherOnlyMixin

logger = logging.getLogger(__name__)


__all__ = (
    'AssignmentSubmissionBaseView', 'EventDetailView',
    'AssignmentAttachmentDownloadView', 'CourseNewsNotificationUpdate',
    'CourseStudentsView', 'AssignmentCommentAttachmentDownloadView',
    'AssignmentCommentUpsertView')


class StudentAssignmentURLParamsMixin:
    """
    Fetches student assignment by URL params and attaches it to the view kwargs.
    """
    student_assignment: StudentAssignment

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.student_assignment = get_object_or_404(self.get_student_assignment_queryset())

    def get_student_assignment_queryset(self):
        return (StudentAssignment.objects
                .filter(pk=self.kwargs['pk'])
                .select_related('student',
                                'assignee__teacher',
                                'assignment',
                                'assignment__course',
                                'assignment__course__main_branch',
                                'assignment__course__meta_course',
                                'assignment__course__semester'))


class AssignmentCommentUpsertView(StudentAssignmentURLParamsMixin, GenericModelView):
    """Posts a new comment or saves draft"""
    model = AssignmentComment
    request = AuthenticatedHttpRequest

    def form_valid(self, form):
        is_draft = "save-draft" in self.request.POST
        with transaction.atomic():
            new_comment = create_assignment_comment(personal_assignment=self.student_assignment,
                                                    created_by=self.request.user,
                                                    is_draft=is_draft,
                                                    message=form.cleaned_data['text'],
                                                    attachment=form.cleaned_data['attached_file'])
        if new_comment.text:
            comment_persistence.add_to_gc(new_comment.text)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        msg = "<br>".join("<br>".join(errors)
                          for errors in form.errors.values())
        messages.error(self.request, "Данные не сохранены!<br>" + msg)
        return HttpResponseRedirect(redirect_to=self.get_error_url())

    def post(self, request, *args, **kwargs):
        form = AssignmentCommentForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        raise NotImplementedError

    def get_error_url(self):
        raise NotImplementedError


class AssignmentSubmissionBaseView(StudentAssignmentURLParamsMixin,
                                   TemplateView):

    def get_student_assignment_queryset(self):
        qs = super().get_student_assignment_queryset()
        submissions = (AssignmentComment.published
                       .select_related('author', 'submission')
                       .prefetch_related('attachments')
                       .order_by('created'))
        return qs.prefetch_related(
            Prefetch('assignmentcomment_set',
                     queryset=submissions),
            Prefetch('assignment__course__course_teachers',
                     queryset=course_teachers_prefetch_queryset(role_priority=False,
                                                                hidden_roles=())),
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
        context = {
            'a_s': sa,
            'time_zone': user.time_zone,
            'first_comment_after_deadline': first_comment_after_deadline,
            'one_teacher': len(sa.assignment.course.course_teachers.all()) == 1,
            'hashes_json': comment_persistence.get_garbage_collection(),
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
    """Download file directly attached to the AssignmentComment"""
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


class AssignmentSubmissionAttachmentDownloadView(ProtectedFileDownloadView):
    """Download file attached to the SubmissionAttachment model"""
    permission_required = ViewAssignmentCommentAttachment.name
    file_field_name = 'attachment'

    def get_protected_object(self) -> Optional[SubmissionAttachment]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (SubmissionAttachment.objects
              .filter(pk=ids[0])
              .select_related("submission__student_assignment__assignment__course"))
        return get_object_or_404(qs)

    def get_permission_object(self):
        return self.protected_object.submission.student_assignment


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
