import datetime
import logging
import os
import posixpath
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, When, Value, Case, \
    prefetch_related_objects
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from nbconvert import HTMLExporter
from vanilla import CreateView

import courses.utils
from core import comment_persistence
from core.utils import hashids, is_club_site
from core.views import LoginRequiredMixin
from courses.models import Course, Semester, AssignmentAttachment
from courses.settings import SemesterTypes
from learning.forms import AssignmentCommentForm, AssignmentScoreForm
from learning.models import StudentAssignment, AssignmentComment, \
    AssignmentNotification, \
    Event
from learning.permissions import course_access_role, CourseRole
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT, \
    ASSIGNMENT_TASK_ATTACHMENT

logger = logging.getLogger(__name__)

DROP_ATTACHMENT_LINK = """
<a href="{0}"><i class="fa fa-trash-o"></i>&nbsp;{1}</a>"""

__all__ = [
    # mixins
    'AssignmentProgressBaseView',
    # views
    'CoursesListView', 'StudentAssignmentTeacherDetailView',
    'EventDetailView',
    'AssignmentAttachmentDownloadView',
    'AssignmentCommentAttachmentDownloadView'
]


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
