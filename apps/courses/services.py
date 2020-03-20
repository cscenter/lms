from typing import Dict, List

from django.db.models import Count, Q

from courses.constants import TeacherRoles
from courses.models import CourseReview, CourseClass


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
    def get_reviews(course):
        reviews = (CourseReview.objects
                   .filter(course__meta_course_id=course.meta_course_id)
                   .select_related('course', 'course__semester',
                                   'course__branch')
                   .only('pk', 'modified', 'text',
                         'course__semester__year', 'course__semester__type',
                         'course__branch__name'))
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
