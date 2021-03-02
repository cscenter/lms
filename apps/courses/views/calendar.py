from typing import Iterable

from django.http import HttpResponseRedirect
from django.views import generic

from core.timezone import now_local
from courses.calendar import CalendarQueryParams, MonthFullWeeksEventsCalendar, \
    WeekEventsCalendar, CalendarEventW

__all__ = ('MonthEventsCalendarView', 'WeekEventsView')

from courses.utils import MonthPeriod


class MonthEventsCalendarView(generic.TemplateView):
    calendar_type = "full"
    template_name = "lms/courses/calendar.html"

    def get(self, request, *args, **kwargs):
        # Get month period from GET-parameters or current month by default
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        today_local = now_local(request.user.time_zone)
        year = query_params.validated_data.get('year', today_local.year)
        month = query_params.validated_data.get('month', today_local.month)
        month_period = MonthPeriod(year, month)
        events = self.get_events(month_period)
        calendar = MonthFullWeeksEventsCalendar(month_period, events)
        context = {
            "today": today_local.date(),
            "calendar_type": self.calendar_type,
            "calendar": calendar
        }
        return self.render_to_response(context)

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable:
        raise NotImplementedError()


class WeekEventsView(generic.TemplateView):
    def get(self, request, *args, **kwargs):
        """Validates GET-parameters, set defaults if no values provided."""
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        today_local = now_local(request.user.time_zone).date()
        today_iso_year, today_iso_week, _ = today_local.isocalendar()
        iso_year = query_params.validated_data.get('year', today_iso_year)
        iso_week = query_params.validated_data.get('week', today_iso_week)
        events = self.get_events(iso_year, iso_week)
        calendar = WeekEventsCalendar(iso_year, iso_week, events)
        context = {
            "calendar": calendar
        }
        return self.render_to_response(context)

    def get_events(self, iso_year, iso_week) -> Iterable[CalendarEventW]:
        raise NotImplementedError()
