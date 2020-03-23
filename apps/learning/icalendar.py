from datetime import datetime
from typing import Iterable, Dict

import pytz
from dateutil.relativedelta import relativedelta
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
                       events: Iterable[Dict]) -> Calendar:
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
    for event in events:
        event_component = ICalendarEvent()
        for k, v in event.items():
            event_component.add(k, v)
        cal.add_component(event_component)
    return cal


class CalendarEventScope:
    TEACHER = 'teaching'
    STUDENT = 'learning'


def get_icalendar_class_event(cc: CourseClass, tz: pytz.timezone,
                              uid, url, categories):
    if cc.description.strip():
        description = "{}\n\n{}".format(cc.description, url)
    else:
        description = url
    starts_at = tz.localize(datetime.combine(cc.date, cc.starts_at))
    ends_at = tz.localize(datetime.combine(cc.date, cc.ends_at))
    return {
        'uid': vText(uid),
        'url': vUri(url),
        'summary': vText(cc.name),
        'description': vText(description),
        'location': vText(cc.venue.address),
        'dtstart': starts_at,
        'dtend': ends_at,
        'dtstamp': timezone.now(),
        'created': cc.created,
        'last-modified': cc.modified,
        'categories': vInline(categories)
    }


def get_icalendar_student_classes(user: User, time_zone, url_builder, domain):
    """Generates icalendar events from individual classes"""
    event_scope = CalendarEventScope.STUDENT
    uid_pattern = f"courseclasses-{user.pk}-{'{}'}-{event_scope}@{domain}"
    cc_related = ['venue',
                  'venue__location',
                  'course',
                  'course__branch',
                  'course__semester',
                  'course__meta_course']
    queryset = (CourseClass.objects
                .filter(course__enrollment__student_id=user.pk,
                        course__enrollment__is_deleted=False)
                .select_related(*cc_related))
    for cc in queryset:
        uid = uid_pattern.format(cc.pk)
        url = url_builder(cc.get_absolute_url())
        categories = [event_scope.upper()]
        event = get_icalendar_class_event(cc, time_zone,
                                          uid, url, categories=categories)
        yield event


def get_icalendar_teacher_classes(user: User, time_zone, url_builder, domain):
    """
    Generates icalendar events from classes where user is participating
    as a teacher.
    """
    event_scope = CalendarEventScope.TEACHER
    uid_pattern = f"courseclasses-{user.pk}-{'{}'}-{event_scope}@{domain}"
    cc_related = ['venue',
                  'venue__location',
                  'course',
                  'course__branch',
                  'course__semester',
                  'course__meta_course']
    queryset = (CourseClass.objects
                .filter(course__teachers=user)
                .select_related(*cc_related))
    for cc in queryset:
        uid = uid_pattern.format(cc.pk)
        url = url_builder(cc.get_absolute_url())
        categories = [event_scope.upper()]
        event = get_icalendar_class_event(cc, time_zone,
                                          uid, url, categories=categories)
        yield event


def get_icalendar_assignment_event(assignment: Assignment, uid, url, categories):
    summary = "{} ({})".format(assignment.title, assignment.course.name)
    starts_at = assignment.deadline_at
    ends_at = starts_at + relativedelta(hours=1)
    categories = 'CSC,ASSIGNMENT,{}'.format(','.join(categories))
    return {
        'uid': vText(uid),
        'url': vUri(url),
        'summary': vText(summary),
        'description': vText(url),
        'dtstart': starts_at,
        'dtend': ends_at,
        'dtstamp': timezone.now(),
        'created': assignment.created,
        'last-modified': assignment.modified,
        'categories': vInline(categories)
    }


def get_icalendar_student_assignments(user: User, url_builder, domain):
    """
    Generates icalendar events from individual assignments with
    future deadline.
    """
    event_scope = CalendarEventScope.STUDENT
    uid_pattern = f"assignments-{user.pk}-{'{}'}-{event_scope}@{domain}"
    queryset = (StudentAssignment.objects
                .filter(student_id=user.pk,
                        assignment__deadline_at__gt=timezone.now())
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__meta_course',
                                'assignment__course__semester'))
    for sa in queryset:
        assignment = sa.assignment
        uid = uid_pattern.format(assignment.pk)
        url = url_builder(sa.get_student_url())
        categories = [event_scope.upper()]
        event = get_icalendar_assignment_event(assignment, uid, url, categories)
        yield event


def get_icalendar_teacher_assignments(user: User, url_builder, domain):
    """
    Generates icalendar events from assignments with future deadline
    where user is participating as a teacher.
    """
    event_scope = CalendarEventScope.TEACHER
    uid_pattern = f"assignments-{user.pk}-{'{}'}-{event_scope}@{domain}"
    queryset = (Assignment.objects
                .filter(course__teachers=user,
                        deadline_at__gt=timezone.now())
                .select_related('course',
                                'course__meta_course',
                                'course__semester'))
    for assignment in queryset:
        uid = uid_pattern.format(assignment.pk)
        url = url_builder(assignment.get_teacher_url())
        categories = [event_scope.upper()]
        event = get_icalendar_assignment_event(assignment, uid, url, categories)
        yield event


def get_icalendar_non_course_events(user: User, time_zone, url_builder, domain):
    """
    Generates icalendar records for all events related to the user branch
    """
    localize = time_zone.localize
    uid_pattern = f"noncourseevents-{'{}'}@{domain}"
    queryset = (Event.objects
                .filter(date__gt=timezone.now())
                .select_related('venue'))
    if hasattr(user, "branch_id") and user.branch_id:
        queryset = queryset.filter(branch_id=user.branch_id)
    for event in queryset:
        uid = uid_pattern.format(event.pk)
        url = url_builder(event.get_absolute_url())
        if event.name.strip():
            description = "{}\n\n{}".format(event.name, url)
        else:
            description = url
        starts_at = localize(datetime.combine(event.date, event.starts_at))
        ends_at = localize(datetime.combine(event.date, event.ends_at))
        icalendar_event = {
            'uid': vText(uid),
            'url': vUri(url),
            'summary': vText(event.name),
            'description': vText(description),
            'dtstart': starts_at,
            'dtend': ends_at,
            'dtstamp': timezone.now(),
            'created': event.created,
            'last-modified': event.modified,
            'categories': vInline('CSC,EVENT')
        }
        yield icalendar_event
