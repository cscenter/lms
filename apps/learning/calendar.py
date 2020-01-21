from itertools import chain

import attr

from courses.calendar import CalendarEvent
from courses.models import CourseClass, Course
from courses.utils import get_terms_for_calendar_month
from learning.models import Event


@attr.s
class LearningCalendarEvent(CalendarEvent):
    @property
    def name(self):
        return self.event.name


def get_month_events(year, month, base_events_qs, base_course_class_qs):
    study_events = (base_events_qs
                    .in_month(year, month)
                    .order_by('date', 'starts_at'))
    classes = (base_course_class_qs
               .for_calendar()
               .in_month(year, month))
    return chain(
        (CalendarEvent(e) for e in classes),
        (LearningCalendarEvent(e) for e in study_events)
    )


def get_student_month_events(user, year, month, personal=False):
    """
    Returns non course events and course classes in the student's home
    branch. Set `personal=True` if needs to filter out classes by courses
    which student enrolled in.
    """
    branches = [user.branch_id]
    events_qs = Event.objects.filter(branch_id__in=branches)
    if personal:
        classes_qs = CourseClass.objects.for_student(user)
    else:
        classes_qs = CourseClass.objects.in_branches(*branches)
    return get_month_events(year, month, events_qs, classes_qs)


def get_teacher_month_events(user, year, month, personal=False):
    """
    Returns non course events and course classes for branches where
    user has been participated as a teacher. Set `personal=True` if
    needs to filter out classes by courses taught by the user.
    """
    branches = get_branches_for_teacher(user, year, month)
    events_qs = Event.objects.filter(branch_id__in=branches)
    if personal:
        classes_qs = CourseClass.objects.for_teacher(user)
    else:
        classes_qs = CourseClass.objects.in_branches(*branches)
    return get_month_events(year, month, events_qs, classes_qs)


def get_branches_for_teacher(user, year, month):
    """
    Returns all branches where user has been participated as a teacher
    """
    term_indexes = [term.index for term in
                    get_terms_for_calendar_month(year, month)]
    branches = set(Course.objects
                   .filter(semester__index__in=term_indexes,
                           teachers=user)
                   .values_list("branch_id", flat=True)
                   .distinct())
    branches.add(user.branch_id)
    return branches
