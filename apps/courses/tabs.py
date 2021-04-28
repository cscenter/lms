"""
Inspired by edx tab implementation
https://github.com/edx/edx-platform/blob/a439d5164c07e4695181b15244e8e5c7681421c4/common/lib/xmodule/xmodule/tabs.py
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, NamedTuple, Optional

from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

from courses.services import CourseService
from courses.tabs_registry import register, registry

# TODO: default tab implementation for `assignments` and `classes` + tests


logger = logging.getLogger(__name__)


READ_ONLY_COURSE_TAB_ATTRIBUTES = ['type']


class InvalidTabException(Exception):
    """
    A complaint about invalid tabs.
    """
    pass


class TabNotFound(Exception):
    """
    A complaint about invalid tabs.
    """
    pass


def validate_keys(expected_keys):
    """
    Returns a function that checks that specified keys are present in a dict.
    """

    def check(actual_dict, raise_error=True):
        """
        Function that checks whether all keys in the expected_keys object
        is in the given actual_dict object.
        """
        missing = set(expected_keys) - set(actual_dict.keys())
        if not missing:
            return True
        if raise_error:
            raise InvalidTabException(
                f"Expected keys '{expected_keys}' are not present "
                f"in the given dict: {actual_dict}")
        else:
            return False

    return check


class CourseTabPanel(NamedTuple):
    # TODO: fetch_func instead?
    context: Dict

    @property
    def has_content(self):
        return len(self.context.get("items", [])) > 0


class CourseTab:
    """
    The Course Tab class is a data abstraction for all tabs  within a course.
    It is an abstract class - to be inherited by various tab types.
    Derived classes are expected to override methods as needed.
    When a new tab class is created, it should define the type and add it in
    this class' factory method.
    """
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def type(self):
        raise NotImplementedError

    # The title of the tab, which should be internationalized using
    # gettext_noop since the user won't be available in this context.
    title = None

    # HTML class to add to the tab page's body, or None if no class it
    # to be added
    body_class = None

    # Class property that specifies whether the tab is hidden for a
    # particular course.
    is_hidden = False

    # The relative priority of this view that affects the ordering
    priority = None

    # True if this tab is dynamically added to the list of tabs
    is_dynamic = False

    # True if this tab is a default for the course (when enabled)
    is_default = True

    # If there is a single view associated with this tab, this is the name of it
    view_name = None

    # Tab panel associated with the tab
    tab_panel = None

    def __init__(self, tab_dict):
        """
        Initializes class members with values passed in by subclasses.
        Args:
            tab_dict (dict) - a dictionary of parameters used to build the tab.
        """
        super().__init__()
        self.name = _(tab_dict.get('name', self.title))
        self.is_hidden = tab_dict.get('is_hidden', self.is_hidden)

        self.tab_dict = tab_dict

    @classmethod
    def is_enabled(cls, course, user):
        """Returns true if this course tab is enabled in the course.
        Args:
            course: the course using the feature
            user: an optional user interacting with the course (defaults to None)
        """
        raise NotImplementedError()

    def __getitem__(self, key):
        """
        This method allows callers to access CourseTab members with the
        d[key] syntax as is done with Python dictionary objects.
        """
        if hasattr(self, key):
            return getattr(self, key, None)
        else:
            raise KeyError(f'Key {key} not present in tab {self.to_json()}')

    def __setitem__(self, key, value):
        """
        This method allows callers to change CourseTab members with
        the d[key]=value syntax as is done with Python dictionary objects.

        Example:
            course_tab['name'] = new_name
        Note:
            the 'type' member can be 'get', but not 'set'.
        """
        if hasattr(self, key) and key not in READ_ONLY_COURSE_TAB_ATTRIBUTES:
            setattr(self, key, value)
        else:
            raise KeyError(f'Key {key} cannot be set in tab {self.to_json()}')

    def __eq__(self, other):
        """
        Overrides the equal operator to check equality of member variables
        rather than the object's address.
        """
        if isinstance(other, str):
            return self.type == other
        elif isinstance(other, CourseTab):
            return self.type == other.type
        return False

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        """
        Validates the given dict-type tab object to ensure it contains
        the expected keys.
        This method should be overridden by subclasses that require certain
        keys to be persisted in the tab.
        """
        return validate_keys(['type'])(tab_dict, raise_error)

    @classmethod
    def load(cls, type_name, **kwargs):
        """
        Constructs a tab of the given type_name.
        Args:
            type_name (str) - the type of tab that should be constructed
            **kwargs - any other keyword arguments needed for constructing this tab
        Returns:
            an instance of the CourseTab subclass that matches the type_name
        """
        json_dict = kwargs.copy()
        json_dict['type'] = type_name
        return cls.from_json(json_dict)

    def to_json(self):
        """
        Serializes the necessary members of the CourseTab object to a
        json-serializable representation.
        This method is overridden by subclasses that have more members to
        serialize.

        Returns:
            a dictionary with keys for the properties of the CourseTab object.
        """
        to_json_val = {'type': self.type, 'name': self.name}
        if self.is_hidden:
            to_json_val.update({'is_hidden': True})
        return to_json_val

    @staticmethod
    def from_json(tab_dict):
        """
        Deserializes a CourseTab from a json-like representation.
        The subclass that is instantiated is determined by the value of
        the 'type' key in the given dict-type tab. The given dict-type tab
        is validated before instantiating the CourseTab object.
        If the tab_type is not recognized, then an exception is logged
        and None is returned.
        The intention is that the user should still be able to use the course
        even if a particular tab is not found for some reason.
        Args:
            tab_dict: a dictionary with keys for the properties of the tab.
        Raises:
            InvalidTabsException if the given tab doesn't have the right keys.
        """
        tab_type_name = tab_dict.get('type')
        if tab_type_name is None:
            logger.error('No type included in tab: %r', tab_dict)
            return None

        if tab_type_name not in registry:
            logger.exception(
                "Unknown tab type %r Known types: %r.",
                tab_type_name,
                registry.registered_types()
            )
            return None
        tab_class = registry[tab_type_name]
        tab_class.validate(tab_dict)
        return tab_class(tab_dict=tab_dict)

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        return None


class CourseTabList:
    def __init__(self, tabs=None):
        self._tabs = {t.type: t for t in tabs if t} if tabs else {}

    def add(self, tab):
        if not isinstance(tab, CourseTab):
            raise TypeError("Provide an instance of CourseTab")
        self._tabs[tab.type] = tab

    def set_active_tab(self, tab_type) -> None:
        if tab_type not in self._tabs:
            raise TabNotFound(f"Can't' set tab {tab_type} as active")
        for t in self._tabs.values():
            t.is_default = (t == tab_type)

    def __iter__(self):
        return iter(self._tabs.values())

    def items(self):
        return self._tabs.items()

    def __getitem__(self, item):
        return self._tabs[item]


def get_course_tab_list(request, course, codes=None):
    """
    Retrieves the course tab list and manipulates the set as necessary
    """
    available_codes = [
        'about',
        'contacts',
        'reviews',
        'classes',
        'assignments',
        'news',
    ]
    if codes:
        to_process = [c for c in codes if c in available_codes]
    else:
        to_process = available_codes
    tabs = (CourseTab.load(c) for c in to_process)
    user = request.user
    tab_list = CourseTabList()
    for tab in tabs:
        if tab and tab.is_enabled(course, user):
            tab_panel = tab.get_tab_panel(course=course, user=user)
            if tab_panel and not tab_panel.has_content:
                tab.is_hidden = True
            elif tab_panel:
                tab.tab_panel = tab_panel
            if not tab.is_hidden:
                tab_list.add(tab)
    return tab_list


@register
class CourseInfoTab(CourseTab):
    """
    The course info view.
    """
    type = 'about'
    title = gettext_noop("CourseTab|About")
    priority = 10
    is_default = True

    @classmethod
    def is_enabled(cls, course, user):
        return True


@register
class CourseClassesTab(CourseTab):
    type = 'classes'
    title = gettext_noop("CourseTab|Classes")
    priority = 40

    @classmethod
    def is_enabled(cls, course, user):
        return True

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        classes = (CourseService.get_classes(course)
                   .annotate(attachments_count=Count('courseclassattachment')))
        return CourseTabPanel(context={
            "items": classes
        })


class CourseAssignmentsTab(CourseTab):
    type = 'assignments'
    title = gettext_noop("CourseTab|Assignments")
    priority = 50

    @classmethod
    def is_enabled(cls, course, user):
        return True
