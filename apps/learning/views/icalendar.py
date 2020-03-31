import itertools
from typing import NamedTuple, Iterable

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import generic

from learning.services import get_student_classes, get_teacher_classes, \
    get_study_events
from learning.icalendar import generate_icalendar, \
    get_icalendar_teacher_assignments, get_icalendar_student_assignments, \
    TeacherAssignmentICalendarEventBuilder, \
    StudyEventICalendarEventBuilder, \
    StudentAssignmentICalendarEventBuilder, TeacherClassICalendarEventBuilder, \
    StudentClassICalendarEventBuilder
from users.models import User


class ICalendarMeta(NamedTuple):
    name: str
    description: str
    file_name: str


# TODO: add secret link for each student
class UserICalendarView(generic.base.View):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        site = self.request.site
        url_builder = request.build_absolute_uri
        product_id = f"-//{site.name} Calendar//{site.domain}//"
        tz = user.get_timezone()
        calendar_meta = self.get_calendar_meta(user, site, url_builder, tz)
        events = self.get_calendar_events(user, site, url_builder, tz)
        cal = generate_icalendar(product_id,
                                 name=calendar_meta.name,
                                 description=calendar_meta.description,
                                 time_zone=tz,
                                 events=events)
        response = HttpResponse(cal.to_ical(),
                                content_type="text/calendar; charset=UTF-8")
        response['Content-Disposition'] = "attachment; filename=\"{}\"".format(
            calendar_meta.file_name)
        return response

    def get_user(self):
        user_id = self.kwargs['pk']
        qs = (User.objects
              .filter(pk=user_id)
              .only("first_name", "last_name", "patronymic", "pk"))
        return get_object_or_404(qs)

    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        raise NotImplementedError

    def get_calendar_events(self, user, site, url_builder, tz) -> Iterable:
        raise NotImplementedError


class ICalClassesView(UserICalendarView):
    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        return ICalendarMeta(
            name="Занятия CSC",
            description=f"Календарь занятий {site.name} ({user.get_full_name()})",
            file_name="csc_classes.ics"
        )

    def get_calendar_events(self, user, site, url_builder, tz):
        event_builder = StudentClassICalendarEventBuilder(tz, url_builder, site)
        # FIXME: filter out past course classes?
        for course_class in get_student_classes(user, with_venue=True):
            yield event_builder.create(course_class, user)
        event_builder = TeacherClassICalendarEventBuilder(tz, url_builder, site)
        for course_class in get_teacher_classes(user, with_venue=True):
            yield event_builder.create(course_class, user)


class ICalAssignmentsView(UserICalendarView):
    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        description = "Календарь сроков выполнения заданий {} ({})".format(
            site.name, user.get_full_name())
        return ICalendarMeta(
            name="Задания CSC",
            description=description,
            file_name="csc_assignments.ics")

    def get_calendar_events(self, user, site, url_builder, tz):
        builder = TeacherAssignmentICalendarEventBuilder(tz, url_builder, site)
        as_teacher = get_icalendar_teacher_assignments(user, builder)
        builder = StudentAssignmentICalendarEventBuilder(tz, url_builder, site)
        as_student = get_icalendar_student_assignments(user, builder)
        return itertools.chain(as_teacher, as_student)


class ICalEventsView(UserICalendarView):
    def get_user(self):
        return self.request.user

    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        return ICalendarMeta(
            name="События CSC",
            description="Календарь общих событий {}".format(site.name),
            file_name="csc_events.ics")

    def get_calendar_events(self, user, site, url_builder, tz):
        event_builder = StudyEventICalendarEventBuilder(tz, url_builder, site)
        filters = []
        future_events = Q(date__gt=timezone.now())
        filters.append(future_events)
        # FIXME: take into account all teacher branches?
        if hasattr(user, "branch_id") and user.branch_id:
            filters.append(Q(branch_id=user.branch_id))
        for e in get_study_events(filters).select_related('venue'):
            yield event_builder.create(e, user)
