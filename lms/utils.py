from collections import OrderedDict
from enum import Enum

from core.urls import reverse


class PublicRouteException(Exception):
    pass


# TODO: remove after migrating to separated public and members parts
class PublicRoute(Enum):
    """
    Mapping for some public url codes to internal route names.
    """
    PROJECTS = ('projects', 'Проекты', 'projects:report_list_reviewers')
    ADMISSION = ('admission', 'Набор', 'admission:interviews')
    LEARNING = ('learning', 'Обучение', 'study:assignment_list')
    TEACHING = ('teaching', 'Преподавание', 'teaching:assignment_list')
    STAFF = ('staff', 'Курирование', 'staff:student_search')

    def __init__(self, code, section_name, url_name):
        self.code = code
        self.section_name = section_name
        self.url_name = url_name

    def __str__(self):
        return self.code

    @property
    def url(self):
        return reverse(self.url_name)

    @property
    def choice(self):
        return self.code, self.section_name

    @classmethod
    def url_by_code(cls, code):
        try:
            return getattr(cls, code.upper()).url
        except AttributeError:
            raise PublicRouteException(f"Code {code} is not supported")

    @classmethod
    def choices(cls):
        return [(o.code, o.section_name) for o in cls.__members__.values()]


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
            terms.setdefault(term.academic_year, []).append(term.type)
            prev_visited = term
    return terms
