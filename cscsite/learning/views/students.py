from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import CreateView, ListView

from core.exceptions import Redirect
from core.utils import is_club_site
from learning import utils
from learning.forms import CourseOfferingPKForm
from learning.models import Useful, Internship, StudentAssignment, Semester, \
    Enrollment, CourseOffering
from learning.viewmixins import StudentCenterAndVolunteerOnlyMixin, \
    ParticipantOnlyMixin, StudentOnlyMixin
from learning.views import AssignmentProgressBaseView
from learning.views.utils import get_student_city_code


class UsefulListView(StudentCenterAndVolunteerOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "useful.html"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.CENTER_SITE_ID)
                .order_by("sort"))


class InternshipListView(StudentCenterAndVolunteerOnlyMixin, generic.ListView):
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
        if user in sa.assignment.course_offering.teachers.all():
            raise Redirect(to=sa.get_teacher_url())
        # If student failed course, deny access when he has no submissions
        # or positive grade
        if sa.student == user:
            co = sa.assignment.course_offering
            if co.failed_by_student(self.request.user):
                if not sa.has_comments(user) and not sa.grade:
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
                        assignment__course_offering__semester=current_semester)
                .order_by('assignment__deadline_at',
                          'assignment__course_offering__course__name',
                          'pk')
                # FIXME: this prefetch doesn't seem to work properly
                .prefetch_related('assignmentnotification_set')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_in = (Enrollment.active
                       .filter(course_offering__semester=self.current_semester,
                               student=self.request.user)
                       .values_list("course_offering", flat=True))
        open_, archive = utils.split_on_condition(
            context['assignment_list'],
            lambda sa: sa.assignment.is_open and
                       sa.assignment.course_offering_id in enrolled_in)
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        user = self.request.user
        # Since this view for students only, check only city settings
        tz_override = None
        if user.city_code and (user.is_student_center or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_code]
        context["tz_override"] = tz_override
        return context


class CourseOfferingEnrollView(StudentOnlyMixin, generic.View):
    def post(self, request, *args, **kwargs):
        # FIXME: Do I need this form, when it just validate course_offering_pk int or not?
        form = CourseOfferingPKForm(data=request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()
        # TODO: validate slug values and so on?
        course_offering = get_object_or_404(
            CourseOffering.objects
                .in_city(self.request.city_code)
                .filter(pk=form.cleaned_data['course_offering_pk'])
                .select_related("semester"))
        # CourseOffering enrollment should be active
        if not course_offering.enrollment_is_open:
            return HttpResponseForbidden()
        # Club students can't enroll on center courses
        if is_club_site() and not course_offering.is_open:
            return HttpResponseForbidden()
        # Students can enroll in only on courses from their city
        city_code = get_student_city_code(self.request)
        if (not course_offering.is_correspondence
                and city_code != course_offering.get_city()):
            return HttpResponseForbidden()
        # Reject if capacity limited and no places available
        # XXX: Race condition
        if course_offering.is_capacity_limited:
            if not course_offering.places_left:
                msg = _("No places available, sorry")
                messages.error(self.request, msg, extra_tags='timeout')
                return HttpResponseRedirect(course_offering.get_absolute_url())
        Enrollment.objects.update_or_create(
            student=self.request.user, course_offering=course_offering,
            defaults={'is_deleted': False})
        if self.request.POST.get('back') == 'course_list_student':
            return redirect('course_list_student')
        else:
            return HttpResponseRedirect(course_offering.get_absolute_url())


class CourseOfferingUnenrollView(StudentOnlyMixin, generic.DeleteView):
    template_name = "learning/simple_delete_confirmation.html"

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super().__init__(*args, **kwargs)

    def get_object(self, _=None):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        enrollment = get_object_or_404(
            Enrollment.objects
            .filter(
                student=self.request.user,
                course_offering__city_id=self.request.city_code,
                course_offering__semester__type=semester_type,
                course_offering__semester__year=year,
                course_offering__course__slug=self.kwargs['course_slug'])
            .select_related("course_offering", "course_offering__semester"))
        self._course_offering = enrollment.course_offering
        if not enrollment.course_offering.enrollment_is_open:
            raise PermissionDenied
        return enrollment

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirmation_text'] = (
            _("Are you sure you want to unenroll "
              "from \"%(course)s\"?")
            % {'course': self.object.course_offering})
        context['confirmation_button_text'] = _("Unenroll")
        return context

    def delete(self, request, *args, **kwargs):
        enrollment = self.get_object()
        Enrollment.objects.filter(pk=enrollment.pk,
                                  is_deleted=False).update(is_deleted=True)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.GET.get('back') == 'course_list_student':
            return reverse('course_list_student')
        else:
            return self._course_offering.get_absolute_url()
