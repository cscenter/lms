from braces.views import UserPassesTestMixin

from learning.models import Enrollment


class ParticipantOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
               (user.is_teacher or user.is_student or user.is_curator))


class TeacherOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
               (user.is_teacher or user.is_curator))


class InterviewerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
                (user.is_interviewer or user.is_curator))


class StudentOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated() and
                (user.is_student or user.is_curator))


class StudentCenterAndVolunteerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_student_center or user.is_volunteer or user.is_curator


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
        # Skip for open CO
        if co.is_open:
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
