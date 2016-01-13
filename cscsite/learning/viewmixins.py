from braces.views import UserPassesTestMixin
from django.conf import settings

from learning.models import AssignmentStudent, CourseOffering, Enrollment


class TeacherOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
               (user.is_teacher or user.is_curator))


class StudentOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
               (user.is_student or user.is_curator))


class CuratorOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_authenticated() and user.is_curator


class FailedCourseContextMixin(object):
    """Set context variable `is_failed_completed_course` to True
    if student failed current completed course."""

    def get_context_data(self, *args, **kwargs):
        context = super(FailedCourseContextMixin,
                        self).get_context_data(*args, **kwargs)

        if "course_offering" not in context:
            raise NotImplementedError(
            '{0} is missing `course_offering` attribute '.format(
                self.__class__.__name__))

        co = context["course_offering"]
        context["is_failed_completed_course"] = False
        # Skip for club site
        if self.request.site.domain == settings.CLUB_DOMAIN:
            return context

        user = self.request.user
        if not co.is_completed or user.is_anonymous() or user.is_curator:
            return context

        if co.is_completed:
            enrollment = Enrollment.objects.filter(student=user,
                                                   course_offering=co).first()
            if enrollment and enrollment.grade in (
            Enrollment.GRADES.unsatisfactory, Enrollment.GRADES.not_graded):
                context["is_failed_completed_course"] = True
        return context
