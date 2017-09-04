from datetime import datetime, time
from itertools import chain, repeat

import pytz
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import generic
from icalendar import vText, vUri, Calendar, Event, Timezone, TimezoneStandard
from icalendar.prop import vInline

from learning.models import CourseClass, StudentAssignment, Assignment, \
    NonCourseEvent
from learning.views.utils import get_user_city_code


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


# TODO: add secret link for each student?
class ICalView(generic.base.View):
    """
    Base view for student *.ics files

    Make sure, all calendars are visible to all users since you can add
    calendar by link.
    """
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        cal = self.init_calendar()
        cal = self.add_events(cal)
        response = HttpResponse(cal.to_ical(),
                                content_type="text/calendar; charset=UTF-8")
        response['Content-Disposition'] = "attachment; filename=\"{}\"".format(
            self.ical_file_name)
        return response

    def get_timezone(self):
        city_code = get_user_city_code(self.request)
        if not city_code:
            city_code = settings.DEFAULT_CITY_CODE
        return settings.TIME_ZONES[city_code]

    def init_calendar(self):
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
        cal = Calendar()
        cal.add('prodid', "-//{} Calendar//{}//".format(
            self.request.site.name, self.request.site.domain))
        cal.add('version', '2.0')
        tz = self.get_timezone()
        tzc = generate_vtimezone(tz)
        cal.add_component(tzc)
        cal.add('X-WR-CALNAME', vText(self.ical_name))
        cal.add('X-WR-TIMEZONE', vText(tz))
        cal.add('X-WR-CALDESC', vText(self.ical_description))
        cal.add('calscale', 'gregorian')
        return cal

    def get_events(self):
        return []

    def add_events(self, calendar):
        for event in self.get_events():
            evt = Event()
            for k, v in event.items():
                evt.add(k, v)
            calendar.add_component(evt)
        return calendar


class ICalClassesView(ICalView):
    ical_file_name = "csc_classes.ics"
    ical_name = "Занятия CSC"

    @property
    def ical_description(self):
        return "Календарь занятий {} ({})".format(
            self.request.site.name, self.request.user.get_full_name())

    def get_events(self):
        tz = self.get_timezone()
        user = self.request.user
        cc_related = ['venue',
                      'course_offering',
                      'course_offering__semester',
                      'course_offering__course']
        as_teacher = (CourseClass.objects
                      .filter(course_offering__teachers=user)
                      .select_related(*cc_related))
        as_student = (CourseClass.objects
                      .filter(course_offering__enrollment__student_id=user.pk,
                              course_offering__enrollment__is_deleted=False)
                      .select_related(*cc_related))

        AS_TEACHER_TYPE, AS_STUDENT_TYPE = 'teaching', 'learning'
        data = chain(zip(repeat(AS_TEACHER_TYPE), as_teacher),
                     zip(repeat(AS_STUDENT_TYPE), as_student))
        for cc_type, cc in data:
            uid = ("courseclasses-{}-{}@compscicenter.ru"
                   .format(cc.pk, cc_type))
            url = self.request.build_absolute_uri(cc.get_absolute_url())
            if cc.description.strip():
                description = "{} ({})".format(cc.description, url)
            else:
                description = url
            categories = 'CSC,CLASS,{}'.format(cc_type.upper())
            dtstart = tz.localize(datetime.combine(cc.date, cc.starts_at))
            dtend = tz.localize(datetime.combine(cc.date, cc.ends_at))
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(cc.name),
                'description': vText(description),
                'location': vText(cc.venue.address),
                'dtstart': dtstart,
                'dtend': dtend,
                'dtstamp': timezone.now(),
                'created': cc.created,
                'last-modified': cc.modified,
                'categories': vInline(categories)
            }
            yield event


class ICalAssignmentsView(ICalView):
    ical_file_name = "csc_assignments.ics"
    ical_name = "Задания CSC"

    @property
    def ical_description(self):
        return "Календарь сроков выполнения заданий {} ({})".format(
            self.request.site.name, self.request.user.get_full_name())

    def get_events(self):
        user = self.request.user
        as_student = (StudentAssignment.objects
                      .filter(student=user,
                              assignment__deadline_at__gt=timezone.now())
                      .select_related('assignment',
                                      'assignment__course_offering',
                                      'assignment__course_offering__course',
                                      'assignment__course_offering__semester'))
        as_teacher = (Assignment.objects
                      .filter(course_offering__teachers=user,
                              deadline_at__gt=timezone.now())
                      .select_related('course_offering',
                                      'course_offering__course',
                                      'course_offering__semester'))

        AS_TEACHER_TYPE, AS_STUDENT_TYPE = 'teaching', 'learning'
        data = chain(zip(repeat(AS_TEACHER_TYPE), as_teacher),
                     zip(repeat(AS_STUDENT_TYPE), as_student))
        for data_type, d in data:
            if data_type.startswith('t'):  # AS_TEACHER_TYPE
                assignment = d
                to_assignment_url = assignment.get_teacher_url()
            else:  # AS_STUDENT_TYPE
                assignment = d.assignment
                to_assignment_url = d.get_student_url()
            url = self.request.build_absolute_uri(to_assignment_url)
            uid = "assignments-{}-{}-{}@{}".format(
                user.pk, assignment.pk, data_type, self.request.site.domain)
            summary = "{} ({})".format(
                assignment.title, assignment.course_offering.course.name)
            categories = 'CSC,ASSIGNMENT,{}'.format(data_type.upper())
            dtstart = assignment.deadline_at
            dtend = assignment.deadline_at + relativedelta(hours=1)
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(summary),
                'description': vText(url),
                'dtstart': dtstart,
                'dtend': dtend,
                'dtstamp': timezone.now(),
                'created': assignment.created,
                'last-modified': assignment.modified,
                'categories': vInline(categories)
            }
            yield event


class ICalEventsView(ICalView):
    ical_file_name = "csc_events.ics"
    ical_name = "События CSC"

    @property
    def ical_description(self):
        return "Календарь общих событий {}".format(self.request.site.name)

    def get_events(self):
        tz = self.get_timezone()
        qs = (NonCourseEvent.objects
              .filter(date__gt=timezone.now())
              .select_related('venue'))
        for nce in qs:
            uid = "noncourseevents-{}@compscicenter.ru".format(nce.pk)
            url = self.request.build_absolute_uri(nce.get_absolute_url())
            if nce.name.strip():
                description = "{} ({})".format(nce.name, url)
            else:
                description = url
            dtstart = tz.localize(datetime.combine(nce.date, nce.starts_at))
            dtend = tz.localize(datetime.combine(nce.date, nce.ends_at))
            event = {
                'uid': vText(uid),
                'url': vUri(url),
                'summary': vText(nce.name),
                'description': vText(description),
                'dtstart': dtstart,
                'dtend': dtend,
                'dtstamp': timezone.now(),
                'created': nce.created,
                'last-modified': nce.modified,
                'categories': vInline('CSC,EVENT')
            }
            yield event
