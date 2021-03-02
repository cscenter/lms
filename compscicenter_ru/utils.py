from typing import List

import attr
from django.conf import settings

from core.urls import reverse


@attr.s(auto_attribs=True, slots=True)
class Tab:
    target: str = attr.ib()
    name: str = attr.ib()
    active: bool = False
    url: str = '#'
    order: int = 0


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

    def sort(self, key=None):
        """If **key** is None sort by tab.order attribute"""
        key = key or (lambda t: t.order)
        new_order = list((key(t), t.target) for t in self._tabs.values())
        new_order.sort()
        self._tabs = {target: self._tabs[target] for _, target in new_order}

    def items(self):
        return self._tabs.items()

    def __iter__(self):
        return iter(self._tabs.values())

    def __getitem__(self, target):
        return self._tabs[target]

    def __contains__(self, item):
        return item in self._tabs
    
    def __len__(self):
        return len(self._tabs)


def course_public_url(course: 'Course', tab=None,
                      default_branch_code=settings.DEFAULT_BRANCH_CODE):
    # Hide links to courses not made by current site
    if course.main_branch.site_id != settings.SITE_ID:
        return None
    url_params = {
        "course_slug": course.meta_course.slug,
        "main_branch_code": course.main_branch.code,
        "semester_year": course.semester.year,
        "semester_type": course.semester.type,
    }
    if tab is None:
        route_name = 'course_detail'
    else:
        route_name = 'course_detail_with_active_tab'
        url_params['tab'] = tab
    return _reverse_with_optional_branch(route_name, default_branch_code,
                                         subdomain=None, kwargs=url_params)


def course_class_public_url(course_class: 'CourseClass',
                            default_branch_code=settings.DEFAULT_BRANCH_CODE):
    url_params = {
        "course_slug": course_class.course.meta_course.slug,
        "main_branch_code": course_class.course.main_branch.code,
        "semester_year": course_class.course.semester.year,
        "semester_type": course_class.course.semester.type,
    }
    return _reverse_with_optional_branch(
        'class_detail',
        default_branch_code,
        kwargs={'pk': course_class.pk, **url_params})


def _reverse_with_optional_branch(viewname, default_branch_code,
                                  subdomain=None, scheme=None,
                                  args=None, kwargs=None, current_app=None):
    if kwargs["main_branch_code"] == default_branch_code:
        kwargs["main_branch_code"] = ""
    slash = "/" if kwargs["main_branch_code"] else ""
    kwargs["branch_trailing_slash"] = slash
    return reverse(viewname, subdomain=subdomain, scheme=scheme, args=args,
                   kwargs=kwargs, current_app=current_app)
