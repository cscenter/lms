from datetime import timedelta
from typing import List, Optional, Tuple

from django.utils.translation import gettext_lazy as _

from learning.settings import GradeTypes, GradingSystems


def grade_to_mark(grade: str) -> int:
    """
    Converts grade to some score for easier grades comparison.

    Assume unsatisfactory > not_graded.
    """
    if grade == GradeTypes.NOT_GRADED or grade == GradeTypes.WITHOUT_GRADE:
        return 0
    elif grade == GradeTypes.ONE:
        return 1
    elif grade == GradeTypes.UNSATISFACTORY or grade == GradeTypes.TWO:
        return 2
    elif grade == GradeTypes.CREDIT or grade == GradeTypes.THREE:
        return 3
    elif grade == GradeTypes.GOOD or grade == GradeTypes.FOUR:
        return 4
    elif grade == GradeTypes.EXCELLENT or grade == GradeTypes.FIVE:
        return 5
    elif grade == GradeTypes.SIX:
        return 6
    elif grade == GradeTypes.SEVEN:
        return 7
    elif grade == GradeTypes.EIGHT:
        return 8
    elif grade == GradeTypes.NINE:
        return 9
    elif grade == GradeTypes.TEN:
        return 10
    raise ValueError("Unknown grade type")


def grade_to_base_system(grade: str):
    if grade in GradeTypes.get_grades_for_grading_system(GradingSystems.BASE):
        return grade
    elif grade in [*GradeTypes.excellent_grades, GradeTypes.CREDIT]:
        return GradeTypes.EXCELLENT
    elif grade in GradeTypes.good_grades:
        return GradeTypes.GOOD
    elif grade in [GradeTypes.FOUR, GradeTypes.FIVE, GradeTypes.SIX]:
        return GradeTypes.CREDIT
    elif grade in GradeTypes.unsatisfactory_grades:
        return GradeTypes.UNSATISFACTORY
    elif grade in GradeTypes.unset_grades:
        return GradeTypes.UNSATISFACTORY


def is_negative_grade(grade) -> bool:
    return grade in GradeTypes.unsatisfactory_grades


def split_on_condition(iterable, predicate) -> Tuple[List, List]:
    true_lst, false_lst = [], []
    for x in iterable:
        if predicate(x):
            true_lst.append(x)
        else:
            false_lst.append(x)
    return true_lst, false_lst


def humanize_duration(execution_time: timedelta) -> Optional[str]:
    if execution_time is not None:
        total_minutes = int(execution_time.total_seconds()) // 60
        hours, minutes = divmod(total_minutes, 60)
        return str(_("{} hrs {:02d} min")).format(hours, minutes)
    return None
