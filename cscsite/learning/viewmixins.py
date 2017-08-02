from braces.views import UserPassesTestMixin
from django.conf import settings
from django.utils.timezone import now

from learning.settings import FOUNDATION_YEAR


class ParticipantOnlyMixin(UserPassesTestMixin):
    """Used on assignment detail page"""
    raise_exception = False

    def test_func(self, user):
        return (user.is_teacher or user.is_curator or user.is_graduate or
                user.is_student)


class TeacherOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated and
               (user.is_teacher or user.is_curator))


class InterviewerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_interviewer or user.is_curator


class ProjectReviewerGroupOnlyMixin(UserPassesTestMixin):
    """Curator must have this group"""
    raise_exception = False

    def test_func(self, user):
        return (user.is_authenticated and
                (user.is_project_reviewer or user.is_curator))


class StudentOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_active_student or user.is_curator


class StudentCenterAndVolunteerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        is_active_student = (user.is_student_center or
                             user.is_volunteer) and not user.is_expelled
        return is_active_student or user.is_curator


class CuratorOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_authenticated and user.is_curator


class ValidateYearMixin(object):
    """Validate query year GET-param"""
    @staticmethod
    def year_is_valid(request):
        today = now().date()
        year = request.GET.get('year', today.year)
        try:
            year = int(year)
        except ValueError:
            return False
        # Note: we can have events in next year
        if not (FOUNDATION_YEAR <= year <= today.year + 1):
            return False
        return True


class ValidateMonthMixin(object):
    """Validate query month GET-param"""
    @staticmethod
    def month_is_valid(request):
        today = now().date()
        month = request.GET.get('month', today.month)
        try:
            month = int(month)
        except ValueError:
            return False
        if not (1 <= month <= 12):
            return False
        return True


class ValidateWeekMixin(object):
    """Validate query week GET-param"""
    @staticmethod
    def week_is_valid(request):
        today = now().date()
        # This returns current week number. Beware: the week's number
        # is as of ISO8601, so 29th of December can be reported as
        # 1st week of the next year.
        today_year, today_week, _ = today.isocalendar()
        week = request.GET.get('week', today_week)
        try:
            week = int(week)
        except ValueError:
            return False
        if week <= 0:
            return False
        return True
