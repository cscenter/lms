from typing import Dict, List

from courses.constants import TeacherRoles
from courses.models import CourseReview, Course, CourseBranch
from courses.utils import get_terms_in_range


def group_teachers(teachers, multiple_roles=False) -> Dict[str, List]:
    """
    Returns teachers grouped by the most priority role.
    Groups are in priority order.

    Set `multiple_roles=True` if you need to take into account
    all teacher roles.
    """
    roles_in_priority = (
        TeacherRoles.LECTURER,  # Lecturer is the most priority role
        TeacherRoles.SEMINAR,
        *TeacherRoles.values.keys()
    )
    grouped = {role: [] for role in roles_in_priority}
    for teacher in teachers:
        for role in grouped:
            if role in teacher.roles:
                grouped[role].append(teacher)
                if not multiple_roles:
                    break
    return {k: v for k, v in grouped.items() if v}


class CourseService:
    @staticmethod
    def sync_branches(course):
        """
        Make sure Course.main_branch is always presented among `Course.branches`
        values and there is only one branch with `.is_main` attribute
        set to True.
        """
        existing_branches = CourseBranch.objects.filter(course=course)
        has_main_branch = False
        for course_branch in existing_branches:
            is_main = (course_branch.branch_id == course.main_branch_id)
            if course_branch.is_main:
                # Case when main branch were changed without
                # updating .branches values. Admin in that case should
                # raise ValidationError
                if not is_main:
                    course_branch.delete()
                else:
                    has_main_branch = True
            elif is_main:
                has_main_branch = True
                course_branch.is_main = True
                course_branch.save(update_fields=['is_main'])
        if not has_main_branch:
            main_course_branch = CourseBranch(course=course,
                                              branch=course.main_branch,
                                              is_main=True)
            main_course_branch.save()

    @staticmethod
    def get_reviews(course):
        reviews = (CourseReview.objects
                   .filter(course__meta_course_id=course.meta_course_id)
                   .select_related('course', 'course__semester',
                                   'course__main_branch')
                   .only('pk', 'modified', 'text',
                         'course__semester__year', 'course__semester__type',
                         'course__main_branch__name'))
        return list(reviews)

    @staticmethod
    def get_contacts(course):
        teachers_by_role = group_teachers(course.course_teachers.all())
        return [ct for g in teachers_by_role.values() for ct in g
                if len(ct.teacher.private_contacts.strip()) > 0]

    @staticmethod
    def get_news(course):
        return course.coursenews_set.all()

    @staticmethod
    def get_classes(course):
        return (course.courseclass_set
                .select_related("venue", "venue__location")
                .order_by("date", "starts_at"))


def get_teacher_branches(user, start_date, end_date):
    """
    Returns branches where user has been participated as a teacher in a
    given period.
    """
    term_indexes = [t.index for t in get_terms_in_range(start_date, end_date)]
    branches = set(Course.objects
                   .filter(semester__index__in=term_indexes,
                           teachers=user)
                   .values_list("main_branch_id", flat=True)
                   .distinct())
    if user.branch_id is not None:
        branches.add(user.branch_id)
    return branches
