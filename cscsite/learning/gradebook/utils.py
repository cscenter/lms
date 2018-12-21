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
    grading_type = GradingSystems.BASE
    if not any(g for g in es
               if g in [GradeTypes.GOOD, GradeTypes.EXCELLENT]):
        grading_type = GradingSystems.BINARY
    if course.grading_type != grading_type:
        course.grading_type = grading_type
        course.save(update_fields=['grading_type'])
