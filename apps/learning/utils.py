from learning.settings import GradeTypes


def grade_to_mark(grade):
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


def is_negative_grade(grade):
    return grade in GradeTypes.unsatisfactory_grades


def split_on_condition(iterable, predicate):
    true_lst, false_lst = [], []
    for x in iterable:
        if predicate(x):
            true_lst.append(x)
        else:
            false_lst.append(x)
    return true_lst, false_lst
