from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable, Iterable, List, Literal, NamedTuple

import pytz
from dateutil.relativedelta import relativedelta
from icalendar import Calendar
from icalendar import Event as ICalEvent
from icalendar import Timezone, TimezoneStandard, vText, vUri
from icalendar.prop import vInline

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from admission.models import Interview
from admission.roles import Roles
from core.urls import reverse
from courses.models import Assignment, CourseClass
from learning.models import Event, StudentAssignment
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
                       events: Iterable[ICalEvent]) -> Calendar:
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


class ICalendarEvent(ABC):
    @abstractmethod
    def get_calendar_event_id(self, instance, user):
        pass

    @abstractmethod
    def _model_to_dict(self, instance):
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

    def create(self, instance, user: User) -> ICalEvent:
        uid = self.get_calendar_event_id(instance, user)
        event_component = ICalEvent(uid=vText(uid))
        event_component.add("dtstamp", timezone.now())
        event_properties = self._model_to_dict(instance)
        for k, v in event_properties.items():
            event_component.add(k, v)
        return event_component


# noinspection PyAbstractClass
class _CourseClassICalendarEvent(ICalendarEvent):
    def _model_to_dict(self, instance: CourseClass):
        url = self.url_builder(instance.get_absolute_url())
        description = "{}\n\n{}".format(instance.description, url).strip()
        return {
            'url': vUri(url),
            'summary': vText(instance.name),
            'description': vText(description),
            'location': vText(instance.venue.address),
            'dtstart': instance.starts_at_local(self.time_zone),
            'dtend': instance.ends_at_local(self.time_zone),
            'created': instance.created,
            'last-modified': instance.modified,
        }


class StudentClassICalendarEvent(_CourseClassICalendarEvent):
    def get_calendar_event_id(self, instance: CourseClass, user):
        return f"courseclasses-{instance.pk}-learning@{self.domain}"

    def create(self, instance, user: User) -> ICalEvent:
        event_component = super().create(instance, user)
        event_component.add('categories', ['CSC', 'CLASS', 'LEARNING'])
        return event_component


class TeacherClassICalendarEvent(_CourseClassICalendarEvent):
    def get_calendar_event_id(self, instance: CourseClass, user):
        return f"courseclasses-{user.pk}-{instance.pk}-teaching@{self.domain}"

    def create(self, instance, user: User) -> ICalEvent:
        event_component = super().create(instance, user)
        event_component.add('categories', ['CSC', 'CLASS', 'TEACHING'])
        return event_component


class TeacherAssignmentICalendarEvent(ICalendarEvent):
    def get_calendar_event_id(self, instance: Assignment, user):
        return f"assignments-{user.pk}-{instance.pk}-teaching@{self.domain}"

    def _model_to_dict(self, instance: Assignment):
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


class StudentAssignmentICalendarEvent(ICalendarEvent):
    def get_calendar_event_id(self, instance: StudentAssignment, user):
        id_ = instance.assignment.pk
        return f"assignments-{user.pk}-{id_}-teaching@{self.domain}"

    def _model_to_dict(self, instance: StudentAssignment):
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


class StudyEventICalendarEvent(ICalendarEvent):
    def get_calendar_event_id(self, instance: Event, user):
        return f"noncourseevents-{instance.pk}@{self.domain}"

    def _model_to_dict(self, instance: Event):
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

class InterviewICalendarEvent(ICalendarEvent):
    def get_calendar_event_id(self, instance: Interview, user):
        return f"interviews-{user.pk}-{instance.pk}-admission@{self.domain}"

    def _model_to_dict(self, instance: Interview):
        absolute_url = self.url_builder(instance.get_absolute_url())
        description = str(instance)
        try:
            summary = f"Собеседование - {instance.get_section_display()} ({instance.slot.stream.get_format_display()})"
            starts_at = instance.slot.datetime_local
            ends_at = instance.slot.datetime_end_local
        except Interview.slot.RelatedObjectDoesNotExist:
            summary = f"Собеседование - {instance.get_section_display()} (Неизвестно)"
            starts_at = instance.date_local()
            ends_at = starts_at + timedelta(minutes=30)
        return {
            'url': vUri(absolute_url),
            'summary': vText(summary),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'created': instance.created,
            'last-modified': instance.modified
        }


class ICalendarURL(NamedTuple):
    code: Literal["classes", "assignments", "events"]
    title: str
    url: str


def get_icalendar_links(account: User,
                        url_builder: Callable[[str], str] = None) -> List[ICalendarURL]:
    if not url_builder:
        url_builder = str
    url_classes = reverse('user_ical_classes',
                          subdomain=settings.LMS_SUBDOMAIN,
                          args=[account.pk])
    url_assignments = reverse('user_ical_assignments',
                              subdomain=settings.LMS_SUBDOMAIN,
                              args=[account.pk])
    url_events = reverse('ical_events', subdomain=settings.LMS_SUBDOMAIN)
    urls = [
        ICalendarURL(code="classes", title=str(_("Classes")), url=url_builder(url_classes)),
        ICalendarURL(code="assignments", title=str(_("Assignments")), url=url_builder(url_assignments)),
        ICalendarURL(code="events", title=str(_("Events")), url=url_builder(url_events)),
    ]
    if Roles.INTERVIEWER in account.roles:
        url_interviews = reverse('user_ical_interviews',
                              subdomain=settings.LMS_SUBDOMAIN,
                              args=[account.pk])
        urls.append(ICalendarURL(code="interviews", title=str(_("Interviews")), url=url_builder(url_interviews)))
    return urls
