from datetime import timedelta
from typing import List, Optional, Tuple

from django.utils.translation import gettext_lazy as _

from courses.constants import AssignmentStatuses
from learning.settings import GradeTypes


def grade_to_mark(grade: str) -> int:
    """
    Converts grade to some score for easier grades comparison.

    Assume unsatisfactory > not_graded.
    """
    if grade == GradeTypes.NOT_GRADED:
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


def get_score_status_changing_message(comment):
    if not isinstance(comment.meta, dict):
        return ""
    new_score = comment.meta.get('score', None)
    new_status = comment.meta.get('status', None)
    old_score = comment.meta.get('old_score', None)
    old_status = comment.meta.get('old_status', None)

    score_changed = old_score != new_score
    status_changed = old_status != new_status
    changing_message = ''
    if new_score is None:
        new_score = "без оценки"
    status_label = AssignmentStatuses(new_status).label
    if score_changed or status_changed:
        if score_changed and status_changed:
            changing_message = f"Оценка и статус задания были изменены. " \
                       f"Новая оценка: {new_score}. Новый статус: {status_label}."
        elif score_changed:
            changing_message = f"Оценка была изменена. Новая оценка: {new_score}."
        else:
            changing_message = f"Статус был изменён. Новый статус: {status_label}."
    return changing_message
