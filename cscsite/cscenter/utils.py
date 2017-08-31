from collections import OrderedDict

from learning.utils import get_term_index_academic_year_starts, \
    get_term_by_index


def group_terms_by_academic_year(courses):
    """
    Group terms by academic year for provided list of courses.

    Example:
        {'2017': ['spring', 'autumn', 'summer'], ...}

    Notes:
        * Courses have to be sorted  by (-year, -semester__index) to make it work
          as expected.
        * Terms in reversed order.
    """
    # TODO: fix reversed?
    terms = OrderedDict()
    prev_visited = object()
    for course in courses:
        term = course.semester
        if term != prev_visited:
            idx = get_term_index_academic_year_starts(term.year, term.type)
            academic_year, _ = get_term_by_index(idx)
            terms.setdefault(academic_year, []).append(term.type)
            prev_visited = term
    return terms