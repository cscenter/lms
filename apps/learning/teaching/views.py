from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import generic
from django.views.generic.edit import BaseUpdateView
from vanilla import TemplateView

from core.utils import render_markdown
from courses.calendar import CalendarEvent
from courses.models import CourseClass, Course
from courses.views.calendar import MonthEventsCalendarView
from learning.forms import AssignmentModalCommentForm
from learning.models import AssignmentComment
from learning.views.utils import get_teacher_city_code
from users.mixins import TeacherOnlyMixin


class TimetableView(TeacherOnlyMixin, MonthEventsCalendarView):
    """
    Shows classes for courses where authorized teacher participate in.
    """
    calendar_type = "teacher"
    template_name = "learning/teaching/timetable.html"

    def get_default_timezone(self):
        return get_teacher_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        qs = (CourseClass.objects
              .in_month(year, month)
              .filter(course__teachers=self.request.user)
              .for_timetable(self.request.user))
        return (CalendarEvent(e) for e in qs)


class CourseStudentsView(TeacherOnlyMixin, TemplateView):
    # raise_exception = True
    template_name = "learning/teaching/course_students.html"

    def get(self, request, *args, **kwargs):
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            raise Http404
        return super().get(request, *args, **kwargs)

    def handle_no_permission(self, request):
        raise Http404

    def get_context_data(self, **kwargs):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        co = get_object_or_404(Course.objects
                               .filter(semester__type=semester_type,
                                       semester__year=year,
                                       meta_course__slug=self.kwargs['course_slug'])
                               .in_city(self.request.city_code))
        return {
            "co": co,
            "enrollments": (co.enrollment_set(manager="active")
                            .select_related("student"))
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