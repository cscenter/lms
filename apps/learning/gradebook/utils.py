from courses.models import Course
from learning.models import Enrollment
from learning.settings import GradingSystems, GradeTypes


def recalculate_course_grading_system(course: Course) -> None:
    """
    If any student has `good` or `excellent` final grade,
    set base grading system.

    Note:
        Emitting model signals like pre_save, post_save, etc.
    """
    es = (Enrollment.active
          .filter(course_id=course.id)
          .values_list("grade", flat=True))
    if all(g == GradeTypes.NOT_GRADED for g in es):
        return
    base_grades = GradeTypes.get_grades_for_grading_system(GradingSystems.BASE)
    binary_grades = GradeTypes.get_grades_for_grading_system(GradingSystems.BINARY)
    grading_type = GradingSystems.BASE
    if all(g in binary_grades for g in es):
        grading_type = GradingSystems.BINARY
    elif any(g not in base_grades for g in es):
        grading_type = GradingSystems.TEN_POINT
    if course.grading_type != grading_type:
        course.grading_type = grading_type
        course.save(update_fields=['grading_type'])
