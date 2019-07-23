from collections import OrderedDict
from enum import Enum
from typing import NamedTuple, List

import attr

from core.urls import reverse
from courses.utils import get_term_index_academic_year_starts, get_term_by_index


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


@attr.s(auto_attribs=True, slots=True)
class Tab:
    target: str = attr.ib()
    name: str = attr.ib()
    active: bool = False
    url: str = '#'


class TabList:
    def __init__(self, tabs: List[Tab] = None):
        self._tabs = {t.target: t for t in tabs if t} if tabs else {}

    def add(self, tab: Tab):
        self._tabs[tab.target] = tab

    def set_active(self, target) -> None:
        for t in self._tabs.values():
            t.active = False
        if target in self._tabs:
            # TODO: warn if tab not found
            self._tabs[target].active = True

    def __iter__(self):
        return iter(self._tabs.values())

    def items(self):
        return self._tabs.items()

    def __getitem__(self, item):
        return self._tabs[item]
