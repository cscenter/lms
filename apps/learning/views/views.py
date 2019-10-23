import datetime
import logging
import os
import posixpath

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseForbidden, HttpResponseNotFound, JsonResponse, \
    HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import generic
from nbconvert import HTMLExporter
from vanilla import TemplateView, CreateView, GenericModelView

from core import comment_persistence
from core.utils import hashids
from core.views import LoginRequiredMixin
from courses.models import AssignmentAttachment
from courses.constants import ASSIGNMENT_TASK_ATTACHMENT
from courses.views.mixins import CourseURLParamsMixin
from learning.forms import AssignmentCommentForm
from learning.models import StudentAssignment, AssignmentComment, \
    AssignmentNotification, Event, CourseNewsNotification
from learning.permissions import course_access_role, CourseRole
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT
from users.mixins import TeacherOnlyMixin

logger = logging.getLogger(__name__)


__all__ = (
    'AssignmentSubmissionBaseView', 'EventDetailView',
    'AssignmentAttachmentDownloadView', 'CourseNewsNotificationUpdate',
    'CourseStudentsView',
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
                                'assignment__course__meta_course',
                                'assignment__course__semester'))


class AssignmentCommentUpsertView(StudentAssignmentURLParamsMixin,
                                  GenericModelView):
    """Post a new comment or save draft"""
    model = AssignmentComment

    def get_drafts(self):
        return (AssignmentComment.objects
                .filter(author=self.request.user,
                        is_published=False,
                        student_assignment=self.student_assignment))

    def post(self, request, *args, **kwargs):
        save_draft = "save-draft" in request.POST
        # Note: should be exactly one record
        draft = self.get_drafts().last()
        if not draft:
            draft = AssignmentComment(student_assignment=self.student_assignment,
                                      author=request.user,
                                      is_published=False)
        draft.is_published = not save_draft
        form = AssignmentCommentForm(data=request.POST, files=request.FILES,
                                     instance=draft)
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
        return self.get_success_url()


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
        # Not sure if it's the best place for this, but it's the simplest one
        user = self.request.user
        (AssignmentNotification.unread
         .filter(student_assignment=sa, user=user)
         .update(is_unread=False))
        # TODO: move to the StudentAssignment model?
        # Let's consider the last minute of the deadline in favor of the student
        deadline_at = sa.assignment.deadline_at + datetime.timedelta(minutes=1)
        cs_after_deadline = (c for c in sa.assignmentcomment_set.all() if
                             c.created >= deadline_at)
        first_comment_after_deadline = next(cs_after_deadline, None)
        draft = (AssignmentComment.objects
                 .filter(author=self.request.user,
                         is_published=False,
                         student_assignment=self.student_assignment)
                 .last())
        comment_form = AssignmentCommentForm(instance=draft)
        context = {
            'a_s': sa,
            'timezone': sa.assignment.course.get_timezone(),
            'first_comment_after_deadline': first_comment_after_deadline,
            'one_teacher': sa.assignment.course.teachers.count() == 1,
            'hashes_json': comment_persistence.get_hashes_json(),
            'comment_form': comment_form
        }
        return context


class EventDetailView(generic.DetailView):
    model = Event
    context_object_name = 'event'
    template_name = "learning/event_detail.html"


# FIXME: move
class ProtectedMediaFileResponse(HttpResponse):
    """
    Files under `media/assignments/` location are protected by nginx `internal`
    directive and could be returned by providing `X-Accel-Redirect`
    response header.
    Without this header the client error 404 (Not Found) is returned.
    Note:
        FileSystemStorage is the main storage for the media/ directory.
    """
    def __init__(self, file_uri, content_disposition='inline', **kwargs):
        """
        file_uri (X-Accel-Redirect header value) is a URL where the contents
        of the file can be accessed if `internal` directive wasn't set.
        In case of FileSystemStorage this URL starts with
        `settings.MEDIA_URL` value.
        """
        super().__init__(**kwargs)
        if content_disposition == 'attachment':
            # FIXME: Does it necessary to delete content type here?
            del self['Content-Type']
            file_name = os.path.basename(file_uri)
            # XXX: Content-Disposition doesn't have appropriate non-ascii
            # symbols support
            self['Content-Disposition'] = f"attachment; filename={file_name}"
        self['X-Accel-Redirect'] = file_uri


# FIXME: move to utils
def export_ipynb_to_html(ipynb_src_path, html_ext='.html'):
    """
    Converts *.ipynb to html and saves the new file in the same directory with
    `html_ext` extension.
    """
    converted_path = ipynb_src_path + html_ext
    if not os.path.exists(converted_path):
        try:
            # TODO: disable warnings 404 for css and ico in media folder for ipynb files?
            html_exporter = HTMLExporter()
            nb_node, _ = html_exporter.from_filename(ipynb_src_path)
            with open(converted_path, 'w') as f:
                f.write(nb_node)
            return True
        except (FileNotFoundError, AttributeError):
            return False
    return True


class AssignmentAttachmentDownloadView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
            if attachment_type not in (ASSIGNMENT_TASK_ATTACHMENT,
                                       ASSIGNMENT_COMMENT_ATTACHMENT):
                return HttpResponseBadRequest()
        except IndexError:
            raise Http404

        user = request.user
        file_field = None
        course = None
        if attachment_type == ASSIGNMENT_TASK_ATTACHMENT:
            qs = (AssignmentAttachment.objects
                  .filter(pk=pk)
                  .select_related("assignment", "assignment__course"))
            assignment_attachment = get_object_or_404(qs)
            course = assignment_attachment.assignment.course
            file_field = assignment_attachment.attachment
        elif attachment_type == ASSIGNMENT_COMMENT_ATTACHMENT:
            qs = (AssignmentComment.published
                  .filter(pk=pk)
                  .select_related("student_assignment__assignment__course"))
            comment = get_object_or_404(qs)
            file_field = comment.attached_file
            course = comment.student_assignment.assignment.course

        if course is None or file_field is None:
            return HttpResponseNotFound()

        # Check that authenticated user has access to the attachments
        role = course_access_role(course=course, user=user)
        if role not in (CourseRole.STUDENT_REGULAR, CourseRole.TEACHER,
                        CourseRole.CURATOR):
            return HttpResponseForbidden()

        media_file_uri = file_field.url
        content_disposition = 'attachment'
        # Convert *.ipynb to html
        if self.request.GET.get("html", False):
            _, ext = posixpath.splitext(media_file_uri)
            if ext == ".ipynb":
                html_ext = ".html"
                exported = export_ipynb_to_html(file_field.path, html_ext)
                if exported:
                    media_file_uri = media_file_uri + html_ext
                    content_disposition = 'inline'

        return ProtectedMediaFileResponse(media_file_uri, content_disposition)


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
            "co": course,
            "enrollments": (course.enrollment_set(manager="active")
                            .select_related("student"))
        }
