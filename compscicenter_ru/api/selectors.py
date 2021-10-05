from typing import Optional

from django.contrib.sites.models import Site
from django.db.models import Prefetch, Q

from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import CourseTeacher
from courses.utils import get_term_index
from users.constants import Roles
from users.managers import UserQuerySet
from users.models import User


def teachers_list(*, site: Site, course: Optional[int] = None) -> UserQuerySet:
    """Returns site teachers except pure reviewers or spectators."""
    # FIXME: cheaper to aggregate courseteacher (see compsciclub.ru TeachersView)
    reviewer = CourseTeacher.roles.reviewer
    spectator = CourseTeacher.roles.spectator
    # `__ne` custom lookup used to filter out teachers without any role or
    # with reviewer role only.
    any_role_except_pure_reviewer_or_spectator = (
        Q(courseteacher__roles__ne=reviewer.mask) &
        Q(courseteacher__roles=~spectator) &
        Q(courseteacher__roles__ne=0)
    )
    filters = [any_role_except_pure_reviewer_or_spectator]
    if course:
        branches = Branch.objects.for_site(site_id=site.pk)
        min_established = min(b.established for b in branches)
        term_index = get_term_index(min_established, SemesterTypes.AUTUMN)
        filters.extend([
            Q(courseteacher__course__meta_course_id=course),
            Q(courseteacher__course__semester__index__gte=term_index)
        ])
    any_role_except_pure_reviewer_or_spectator = (
        Q(roles__ne=reviewer.mask) &
        Q(roles=~spectator) &
        Q(roles__ne=0)
    )
    prefetch_course_teachers = Prefetch(
        "courseteacher_set",
        queryset=(CourseTeacher.objects
                  .filter(any_role_except_pure_reviewer_or_spectator)
                  .select_related("course",
                                  "course__semester")
                  .only("teacher_id",
                        "course__meta_course_id",
                        "course__semester__index")
                  .order_by("teacher_id", "course__meta_course__id",
                            "-course__semester__index")
                  .distinct("teacher_id", "course__meta_course__id"))
    )
    return (User.objects
                .has_role(Roles.TEACHER, site_id=site.pk)
                .filter(*filters)
                .select_related('branch')
                .only("pk", "first_name", "last_name", "patronymic",
                      "username", "cropbox_data", "photo", "branch__code",
                      "gender", "workplace")
                .distinct("last_name", "first_name", "pk")
                .prefetch_related(prefetch_course_teachers)
                .order_by("last_name", "first_name", "pk"))
