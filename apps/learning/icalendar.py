from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Callable

import pytz
from dateutil.relativedelta import relativedelta
from django.contrib.sites.models import Site
from django.utils import timezone
from icalendar import vText, vUri, Calendar, Event as ICalendarEvent, \
    Timezone, TimezoneStandard
from icalendar.prop import vInline

from courses.models import CourseClass, Assignment
from learning.models import StudentAssignment, Event
from users.models import User


def generate_vtimezone(tz: pytz.timezone):
    assert tz is not pytz.UTC
    tzc = Timezone()
    tzc.add('TZID', tz)
    tzc.add('X-LIC-LOCATION', tz)
    std_comp = TimezoneStandard()
    std_comp.add('TZOFFSETFROM', tz._transition_info[-1][0])
    std_comp.add('TZOFFSETTO', tz._transition_info[-1][0])
    std_comp.add('TZNAME', tz._transition_info[-1][2])
    std_comp.add('DTSTART', datetime.utcfromtimestamp(0))
    tzc.add_component(std_comp)
    return tzc


def generate_icalendar(product_id: str,
                       name: str,
                       description: str,
                       time_zone: pytz.timezone,
                       events: Iterable[ICalendarEvent]) -> Calendar:
    """
    Creates VTIMEZONE component like in a google calendar.

    Google calendar doesn't provide "honest" implementation
    (based on RFC) for `VTIMEZONE` component. Just a stub with current
    daylight/standard offsets. Also, it has custom `X-WR-TIMEZONE` header
    with timezone info. The same for Outlook.

    Note:
        http://tzurl.org/ project implements conversion of IANA
        tzdata into iCalendar VTIMEZONE objects.

    :param product_id: globally unique identifier
    :param name: Calendar display name
    :param description: Calendar description
    :param time_zone: Time zone of the events
    :param events: Calendar events
    :return: Calendar object
    """
    cal = Calendar()
    cal.add('prodid', product_id)
    cal.add('version', '2.0')
    timezone_component = generate_vtimezone(time_zone)
    cal.add_component(timezone_component)
    cal.add('X-WR-CALNAME', vText(name))
    cal.add('X-WR-TIMEZONE', vText(time_zone))
    cal.add('X-WR-CALDESC', vText(description))
    cal.add('calscale', 'gregorian')
    for event_component in events:
        cal.add_component(event_component)
    return cal


class ICalendarEventBuilder(ABC):
    @abstractmethod
    def model_to_dict(self, instance, uid, event_scope):
        pass

    def __init__(self, time_zone: pytz.timezone,
                 url_builder: Callable[[str], str],
                 site: Site):
        # Local dates will be present in this time zone
        self.time_zone = time_zone
        # Must return absolute URL
        self.url_builder = url_builder
        # Domain name is a part of the UID for the calendar component
        self.domain = site.domain

    @property
    def localize(self):
        return self.time_zone.localize

    def create(self, instance, uid, event_scope=None) -> ICalendarEvent:
        event_items = self.model_to_dict(instance, uid, event_scope)
        event_component = ICalendarEvent()
        for k, v in event_items.items():
            event_component.add(k, v)
        return event_component


class CourseClassICalendarEventBuilder(ICalendarEventBuilder):
    def model_to_dict(self, instance: CourseClass, uid, event_scope):
        absolute_url = self.url_builder(instance.get_absolute_url())
        description = "{}\n\n{}".format(instance.description, absolute_url).strip()
        starts_at = self.localize(datetime.combine(instance.date, instance.starts_at))
        ends_at = self.localize(datetime.combine(instance.date, instance.ends_at))
        categories = 'CSC,CLASS,{}'.format(event_scope.upper())
        return {
            'uid': vText(uid),
            'url': vUri(absolute_url),
            'summary': vText(instance.name),
            'description': vText(description),
            'location': vText(instance.venue.address),
            'dtstart': starts_at,
            'dtend': ends_at,
            'dtstamp': timezone.now(),
            'created': instance.created,
            'last-modified': instance.modified,
            'categories': vInline(categories)
        }


class AssignmentICalendarEventBuilder(ICalendarEventBuilder):
    def model_to_dict(self, instance: Assignment, uid, event_scope):
        absolute_url = self.url_builder(instance.get_teacher_url())
        description = absolute_url
        summary = "{} ({})".format(instance.title, instance.course.name)
        starts_at = instance.deadline_at
        ends_at = starts_at + relativedelta(hours=1)
        categories = 'CSC,ASSIGNMENT,{}'.format(event_scope.upper())
        return {
            'uid': vText(uid),
            'url': vUri(absolute_url),
            'summary': vText(summary),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'dtstamp': timezone.now(),
            'created': instance.created,
            'last-modified': instance.modified,
            'categories': vInline(categories)
        }


class StudentAssignmentICalendarEventBuilder(ICalendarEventBuilder):
    def model_to_dict(self, instance: StudentAssignment, uid, event_scope):
        assignment = instance.assignment
        absolute_url = self.url_builder(instance.get_student_url())
        description = absolute_url
        summary = "{} ({})".format(assignment.title, assignment.course.name)
        starts_at = assignment.deadline_at
        ends_at = starts_at + relativedelta(hours=1)
        categories = 'CSC,ASSIGNMENT,{}'.format(event_scope.upper())
        return {
            'uid': vText(uid),
            'url': vUri(absolute_url),
            'summary': vText(summary),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'dtstamp': timezone.now(),
            'created': assignment.created,
            'last-modified': assignment.modified,
            'categories': vInline(categories)
        }


class NonCourseEventICalendarEventBuilder(ICalendarEventBuilder):
    def model_to_dict(self, instance: Event, uid, event_scope):
        absolute_url = self.url_builder(instance.get_absolute_url())
        description = "{}\n\n{}".format(instance.name, absolute_url).strip()
        starts_at = self.localize(datetime.combine(instance.date, instance.starts_at))
        ends_at = self.localize(datetime.combine(instance.date, instance.ends_at))
        return {
            'uid': vText(uid),
            'url': vUri(absolute_url),
            'summary': vText(instance.name),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'dtstamp': timezone.now(),
            'created': instance.created,
            'last-modified': instance.modified,
            'categories': vInline('CSC,EVENT')
        }


class CalendarEventScope:
    TEACHER = 'teaching'
    STUDENT = 'learning'


def get_icalendar_student_classes(user: User,
                                  event_builder: ICalendarEventBuilder) -> Iterable[ICalendarEvent]:
    """Generates icalendar events from individual classes"""
    event_scope = CalendarEventScope.STUDENT
    uid_pattern = f"courseclasses-{user.pk}-{'{}'}-{event_scope}@{event_builder.domain}"
    queryset = (CourseClass.objects
                .for_student(user)
                .select_calendar_data()
                .select_related('venue', 'venue__location'))
    for cc in queryset:
        uid = uid_pattern.format(cc.pk)
        yield event_builder.create(cc, uid, event_scope)


def get_icalendar_teacher_classes(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar events from classes where user is participating
    as a teacher.
    """
    event_scope = CalendarEventScope.TEACHER
    uid_pattern = f"courseclasses-{user.pk}-{'{}'}-{event_scope}@{event_builder.domain}"
    queryset = (CourseClass.objects
                .for_teacher(user)
                .select_calendar_data()
                .select_related('venue', 'venue__location'))
    for cc in queryset:
        uid = uid_pattern.format(cc.pk)
        yield event_builder.create(cc, uid, event_scope)


def get_icalendar_student_assignments(user: User,
                                      event_builder: ICalendarEventBuilder):
    event_scope = CalendarEventScope.STUDENT
    uid_pattern = f"assignments-{user.pk}-{'{}'}-{event_scope}@{event_builder.domain}"
    queryset = (StudentAssignment.objects
                .for_user(user)
                .with_future_deadline())
    for sa in queryset:
        uid = uid_pattern.format(sa.assignment.pk)
        yield event_builder.create(sa, uid, event_scope)


def get_icalendar_teacher_assignments(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar events from assignments with future deadline
    where user is participating as a teacher.
    """
    event_scope = CalendarEventScope.TEACHER
    uid_pattern = f"assignments-{user.pk}-{'{}'}-{event_scope}@{event_builder.domain}"
    queryset = (Assignment.objects
                .filter(course__teachers=user)
                .with_future_deadline()
                .select_related('course',
                                'course__meta_course',
                                'course__semester'))
    for assignment in queryset:
        uid = uid_pattern.format(assignment.pk)
        yield event_builder.create(assignment, uid, event_scope)


def get_icalendar_non_course_events(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar records for all events related to the user branch
    """
    uid_pattern = f"noncourseevents-{'{}'}@{event_builder.domain}"
    queryset = (Event.objects
                .filter(date__gt=timezone.now())
                .select_related('venue'))
    if hasattr(user, "branch_id") and user.branch_id:
        queryset = queryset.filter(branch_id=user.branch_id)
    for event in queryset:
        uid = uid_pattern.format(event.pk)
        yield event_builder.create(event, uid)
