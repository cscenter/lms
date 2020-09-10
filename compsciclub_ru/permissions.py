import rules

from auth.utils import override_perm
from courses.models import Course
from learning.permissions import ViewCourseNews


class ClubCourseViewNews(ViewCourseNews):
    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        return True


override_perm(ClubCourseViewNews)
