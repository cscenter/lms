from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import CreateView, ListView

from core.exceptions import Redirect
from courses.models import Semester
from learning import utils
from learning.enrollment import course_failed_by_student
from learning.models import Useful, Internship, StudentAssignment, Enrollment
from learning.viewmixins import StudentOnlyMixin
from learning.views import AssignmentProgressBaseView


class UsefulListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "useful.html"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.SITE_ID)
                .order_by("sort"))


class InternshipListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/internships.html"

    def get_queryset(self):
        return (Internship.objects
                .order_by("sort"))


class StudentAssignmentStudentDetailView(AssignmentProgressBaseView,
                                         CreateView):
    user_type = 'student'

    def has_permissions_coarse(self, user):
        # Expelled students can't send new submissions or comments
        if self.request.method == "POST":
            is_student = user.is_active_student
        else:
            is_student = user.is_student
        return (is_student or user.is_curator or user.is_graduate or
                user.is_teacher)

    def has_permissions_precise(self, user):
        sa = self.student_assignment
        # Redirect actual course teacher to teaching/ section
        if user in sa.assignment.course.teachers.all():
            raise Redirect(to=sa.get_teacher_url())
        # If student failed course, deny access when he has no submissions
        # or positive grade
        if sa.student == user:
            co = sa.assignment.course
            if course_failed_by_student(co, self.request.user):
                if not sa.has_comments(user) and not sa.score:
                    return False
        return sa.student == user or user.is_curator

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        # Update `text` label if student has no submissions yet
        sa = self.student_assignment
        if sa.assignment.is_online and not sa.has_comments(self.request.user):
            context['form'].fields.get('text').label = _("Add solution")
        return context

    def get_success_url(self):
        return self.student_assignment.get_student_url()


class StudentAssignmentListView(StudentOnlyMixin, ListView):
    """ Show assignments from current semester only. """
    model = StudentAssignment
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_student.html"

    def get_queryset(self):
        current_semester = Semester.get_current()
        self.current_semester = current_semester
        return (StudentAssignment.objects
                .filter(student=self.request.user,
                        assignment__course__semester=current_semester)
                .order_by('assignment__deadline_at',
                          'assignment__course__meta_course__name',
                          'pk')
                # FIXME: this prefetch doesn't seem to work properly
                .prefetch_related('assignmentnotification_set')
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__meta_course',
                                'assignment__course__semester',
                                'student'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_in = (Enrollment.active
                       .filter(course__semester=self.current_semester,
                               student=self.request.user)
                       .values_list("course", flat=True))
        open_, archive = utils.split_on_condition(
            context['assignment_list'],
            lambda sa: sa.assignment.is_open and
                       sa.assignment.course_id in enrolled_in)
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        user = self.request.user
        # Since this view for students only, check only city settings
        tz_override = None
        if user.city_code and (user.is_student or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_code]
        context["tz_override"] = tz_override
        return context
