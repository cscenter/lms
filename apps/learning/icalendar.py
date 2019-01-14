from abc import ABC, abstractmethod
from datetime import datetime
from itertools import chain, repeat

import pytz
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone
from icalendar import vText, vUri, Calendar, Event, Timezone, TimezoneStandard
from icalendar.prop import vInline

from courses.models import CourseClass, Assignment
from learning.models import StudentAssignment, NonCourseEvent
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


class UserEventsICalendar(ABC):
    """
    Generates iCalendar for requested user. Supports only one time zone.

    Timezone should be consistent across all events (although iCalendar
    specification allows multiple VTIMEZONE's). With this assumption we rely on
        * requested user timezone for classes and assignments and on
        * requesting user timezone for non-course events
    (it's much easier to calculate event timezone based on user data than
    on event location)
    """
    TEACHER_EVENT = 'teaching'
    STUDENT_EVENT = 'learning'

    @property
    @abstractmethod
    def file_name(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def title(self):
        """X-WR-CALNAME value"""
        raise NotImplementedError()

    def __init__(self, site: Site, user: User, abs_url_builder, events=None,
                 **kwargs):
        """
        On August 2017 we haven't stable library for conversion `pytz.timezone`
        object to `VTIMEZONE` component.
        Even http://tzurl.org/ project which provided full (since 1970)
        VTIMEZONE implementation have bug for Moscow timezone.

        Google calendar doesn't provide "honest" implementation
        (based on RFC) for `VTIMEZONE` component. Just a stub with current
        daylight/standard offsets. Also, it has custom `X-WR-TIMEZONE` header
        with timezone info.
        The same for Outlook.

        Since we haven't recurrent events in our icalendar's and no
        daylight/standard transitions for SPB, KZN, NSK, let's manually
        create VTIMEZONE components like in google calendar. fck t
        """
        self.site = site
        self.user = user
        self.timezone = self.get_timezone(user)
        self.abs_url_builder = abs_url_builder
        cal = Calendar()
        cal.add('prodid', f"-//{site.name} Calendar//{site.domain}//")
        cal.add('version', '2.0')
        tzc = generate_vtimezone(self.timezone)
        cal.add_component(tzc)
        cal.add('X-WR-CALNAME', vText(self.title))
        cal.add('X-WR-TIMEZONE', vText(self.timezone))
        cal_description = self.get_description(**kwargs)
        cal.add('X-WR-CALDESC', vText(cal_description))
        cal.add('calscale', 'gregorian')
        self.cal = cal
        events = events or self.get_events()
        for event in events:
            evt = Event()
            for k, v in event.items():
                evt.add(k, v)
            self.cal.add_component(evt)

    def get_timezone(self, user: User):
        city_code = user.city_code
        if not city_code:
            city_code = settings.DEFAULT_CITY_CODE
        return settings.TIME_ZONES[city_code]

    def get_description(self, **kwargs):
        return ""

    def get_events(self):
        return []

    def to_ical(self):
        return self.cal.to_ical()


class UserClassesICalendar(UserEventsICalendar):
    file_name = "csc_classes.ics"
    title = "Занятия CSC"

    def get_description(self):
        return f"Календарь занятий {self.site.name} ({self.user.get_full_name()})"

    def get_events(self):
        localize = self.timezone.localize
        cc_related = ['venue',
                      'course',
                      'course__semester',
                      'course__meta_course']
        as_teacher = (CourseClass.objects
                      .filter(course__teachers=self.user)
                      .select_related(*cc_related))
        as_student = (CourseClass.objects
                      .filter(course__enrollment__student_id=self.user.pk,
                              course__enrollment__is_deleted=False)
                      .select_related(*cc_related))

        data = chain(zip(repeat(self.TEACHER_EVENT), as_teacher),
                     zip(repeat(self.STUDENT_EVENT), as_student))
        for cc_type, cc in data:
            uid = f"courseclasses-{cc.pk}-{cc_type}@compscicenter.ru"
            url = self.abs_url_builder(cc.get_absolute_url())
            if cc.description.strip():
                description = "{}\n\n{}".format(cc.description, url)
            else:
                description = url
            categories = 'CSC,CLASS,{}'.format(cc_type.upper())
            start = localize(datetime.combine(cc.date, cc.starts_at))
            end = localize(datetime.combine(cc.date, cc.ends_at))
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(cc.name),
                'description': vText(description),
                'location': vText(cc.venue.address),
                'dtstart': start,
                'dtend': end,
                'dtstamp': timezone.now(),
                'created': cc.created,
                'last-modified': cc.modified,
                'categories': vInline(categories)
            }
            yield event


class UserAssignmentsICalendar(UserEventsICalendar):
    file_name = "csc_assignments.ics"
    title = "Задания CSC"

    def get_description(self):
        return "Календарь сроков выполнения заданий {} ({})".format(
            self.site.name, self.user.get_full_name())

    def get_events(self):
        as_student = (StudentAssignment.objects
                      .filter(student_id=self.user.pk,
                              assignment__deadline_at__gt=timezone.now())
                      .select_related('assignment',
                                      'assignment__course',
                                      'assignment__course__meta_course',
                                      'assignment__course__semester'))
        as_teacher = (Assignment.objects
                      .filter(course__teachers=self.user,
                              deadline_at__gt=timezone.now())
                      .select_related('course',
                                      'course__meta_course',
                                      'course__semester'))

        data = chain(zip(repeat(self.TEACHER_EVENT), as_teacher),
                     zip(repeat(self.STUDENT_EVENT), as_student))
        for data_type, d in data:
            if data_type == self.TEACHER_EVENT:
                assignment = d
                to_assignment_url = assignment.get_teacher_url()
            else:  # Student event
                assignment = d.assignment
                to_assignment_url = d.get_student_url()
            url = self.abs_url_builder(to_assignment_url)
            uid = "assignments-{}-{}-{}@{}".format(
                self.user.pk, assignment.pk, data_type, self.site.domain)
            summary = "{} ({})".format(
                assignment.title, assignment.course.meta_course.name)
            categories = 'CSC,ASSIGNMENT,{}'.format(data_type.upper())
            start = assignment.deadline_at
            end = assignment.deadline_at + relativedelta(hours=1)
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(summary),
                'description': vText(url),
                'dtstart': start,
                'dtend': end,
                'dtstamp': timezone.now(),
                'created': assignment.created,
                'last-modified': assignment.modified,
                'categories': vInline(categories)
            }
            yield event


# FIXME: Filter events by requesting user location?
class EventsICalendar(UserEventsICalendar):
    """Shows all events in the timezone of the requesting user"""
    file_name = "csc_events.ics"
    title = "События CSC"

    def get_description(self):
        return "Календарь общих событий {}".format(self.site.name)

    def get_events(self):
        localize = self.timezone.localize
        qs = (NonCourseEvent.objects
              .filter(date__gt=timezone.now())
              .select_related('venue'))
        for nce in qs:
            uid = "noncourseevents-{}@compscicenter.ru".format(nce.pk)
            url = self.abs_url_builder(nce.get_absolute_url())
            if nce.name.strip():
                description = "{}\n\n{}".format(nce.name, url)
            else:
                description = url
            start = localize(datetime.combine(nce.date, nce.starts_at))
            end = localize(datetime.combine(nce.date, nce.ends_at))
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(nce.name),
                'description': vText(description),
                'dtstart': start,
                'dtend': end,
                'dtstamp': timezone.now(),
                'created': nce.created,
                'last-modified': nce.modified,
                'categories': vInline('CSC,EVENT')
            }
            yield event
