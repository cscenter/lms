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
    def get_calendar_event_id(self, instance, user):
        pass

    @abstractmethod
    def model_to_dict(self, instance):
        """
        Check https://tools.ietf.org/rfc/rfc5545.txt for the list of properties.
        """
        return {}

    def __init__(self, time_zone: pytz.timezone,
                 url_builder: Callable[[str], str],
                 site: Site):
        """

        :param time_zone: Local dates will be present in this time zone
        :param url_builder: Callable returns absolute URL
        :param site: Created events will be under namespace of the site domain
        """
        self.time_zone = time_zone
        self.url_builder = url_builder
        # Domain name is a part of the UID for the calendar component
        self.domain = site.domain

    def create(self, instance, user: User) -> ICalendarEvent:
        uid = self.get_calendar_event_id(instance, user)
        event_component = ICalendarEvent(uid=vText(uid), dtstamp=timezone.now())
        event_properties = self.model_to_dict(instance)
        for k, v in event_properties.items():
            event_component.add(k, v)
        self.post_create(event_component, instance)
        return event_component

    def post_create(self, event_component: ICalendarEvent, instance):
        pass


# noinspection PyAbstractClass
class CourseClassICalendarEventBuilder(ICalendarEventBuilder):
    def model_to_dict(self, instance: CourseClass):
        url = self.url_builder(instance.get_absolute_url())
        description = "{}\n\n{}".format(instance.description, url).strip()
        starts_at = datetime.combine(instance.date, instance.starts_at)
        ends_at = datetime.combine(instance.date, instance.ends_at)
        return {
            'url': vUri(url),
            'summary': vText(instance.name),
            'description': vText(description),
            'location': vText(instance.venue.address),
            'dtstart': self.time_zone.localize(starts_at),
            'dtend': self.time_zone.localize(ends_at),
            'created': instance.created,
            'last-modified': instance.modified,
        }


class StudentClassICalendarEventBuilder(CourseClassICalendarEventBuilder):
    def get_calendar_event_id(self, instance: CourseClass, user):
        return f"courseclasses-{instance.pk}-learning@{self.domain}"

    def post_create(self, event_component, instance):
        event_component.add('categories', ['CSC', 'CLASS', 'LEARNING'])


class TeacherClassICalendarEventBuilder(CourseClassICalendarEventBuilder):
    def get_calendar_event_id(self, instance: CourseClass, user):
        return f"courseclasses-{user.pk}-{instance.pk}-teaching@{self.domain}"

    def post_create(self, event_component, instance):
        event_component.add('categories', ['CSC', 'CLASS', 'TEACHING'])


class TeacherAssignmentICalendarEventBuilder(ICalendarEventBuilder):
    def get_calendar_event_id(self, instance: Assignment, user):
        return f"assignments-{user.pk}-{instance.pk}-teaching@{self.domain}"

    def model_to_dict(self, instance: Assignment):
        absolute_url = self.url_builder(instance.get_teacher_url())
        description = absolute_url
        summary = "{} ({})".format(instance.title, instance.course.name)
        starts_at = instance.deadline_at
        ends_at = starts_at + relativedelta(hours=1)
        return {
            'url': vUri(absolute_url),
            'summary': vText(summary),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'created': instance.created,
            'last-modified': instance.modified,
            'categories': ['CSC', 'ASSIGNMENT', 'TEACHING']
        }


class StudentAssignmentICalendarEventBuilder(ICalendarEventBuilder):
    def get_calendar_event_id(self, instance: StudentAssignment, user):
        id_ = instance.assignment.pk
        return f"assignments-{user.pk}-{id_}-teaching@{self.domain}"

    def model_to_dict(self, instance: StudentAssignment):
        assignment = instance.assignment
        absolute_url = self.url_builder(instance.get_student_url())
        description = absolute_url
        summary = "{} ({})".format(assignment.title, assignment.course.name)
        starts_at = assignment.deadline_at
        ends_at = starts_at + relativedelta(hours=1)
        return {
            'url': vUri(absolute_url),
            'summary': vText(summary),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'created': assignment.created,
            'last-modified': assignment.modified,
            'categories': ['CSC', 'ASSIGNMENT', 'LEARNING']
        }


class NonCourseEventICalendarEventBuilder(ICalendarEventBuilder):
    def get_calendar_event_id(self, instance: Event, user):
        return f"noncourseevents-{instance.pk}@{self.domain}"

    def model_to_dict(self, instance: Event):
        absolute_url = self.url_builder(instance.get_absolute_url())
        description = "{}\n\n{}".format(instance.name, absolute_url).strip()
        starts_at = datetime.combine(instance.date, instance.starts_at)
        ends_at = datetime.combine(instance.date, instance.ends_at)
        return {
            'url': vUri(absolute_url),
            'summary': vText(instance.name),
            'description': vText(description),
            'dtstart': self.time_zone.localize(starts_at),
            'dtend': self.time_zone.localize(ends_at),
            'created': instance.created,
            'last-modified': instance.modified,
            'categories': vInline('CSC,EVENT')
        }


def get_icalendar_student_classes(user: User,
                                  event_builder: ICalendarEventBuilder) -> Iterable[ICalendarEvent]:
    """Generates icalendar events from individual classes"""
    queryset = (CourseClass.objects
                .for_student(user)
                .select_calendar_data()
                .select_related('venue', 'venue__location'))
    for cc in queryset:
        yield event_builder.create(cc, user)


def get_icalendar_teacher_classes(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar events from classes where user is participating
    as a teacher.
    """
    queryset = (CourseClass.objects
                .for_teacher(user)
                .select_calendar_data()
                .select_related('venue', 'venue__location'))
    for cc in queryset:
        yield event_builder.create(cc, user)


def get_icalendar_student_assignments(user: User,
                                      event_builder: ICalendarEventBuilder):
    queryset = (StudentAssignment.objects
                .for_user(user)
                .with_future_deadline())
    for sa in queryset:
        yield event_builder.create(sa, user)


def get_icalendar_teacher_assignments(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar events from assignments with future deadline
    where user is participating as a teacher.
    """
    queryset = (Assignment.objects
                .filter(course__teachers=user)
                .with_future_deadline()
                .select_related('course',
                                'course__meta_course',
                                'course__semester'))
    for assignment in queryset:
        yield event_builder.create(assignment, user)


def get_icalendar_non_course_events(user: User, event_builder: ICalendarEventBuilder):
    """
    Generates icalendar records for all events related to the user branch
    """
    queryset = (Event.objects
                .filter(date__gt=timezone.now())
                .select_related('venue'))
    if hasattr(user, "branch_id") and user.branch_id:
        queryset = queryset.filter(branch_id=user.branch_id)
    for event in queryset:
        yield event_builder.create(event, user)
