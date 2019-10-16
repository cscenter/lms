from typing import Iterable, Union

from django.http import HttpResponseRedirect
from django.views import generic

from core.timezone import now_local, CityCode, Timezone
from courses.calendar import CalendarQueryParams, MonthFullWeeksEventsCalendar, \
    WeekEventsCalendar, CalendarEvent

__all__ = ('MonthEventsCalendarView', 'WeekEventsView')


class MonthEventsCalendarView(generic.TemplateView):
    calendar_type = "full"
    template_name = "courses/calendar.html"

    def get(self, request, *args, **kwargs):
        """Validates GET-parameters, set defaults if no values provided."""
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        today_local = now_local(request.user.get_timezone()).date()
        year = query_params.validated_data.get('year', today_local.year)
        month = query_params.validated_data.get('month', today_local.month)
        context = self.get_context_data(year, month, today_local, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, year, month, today, **kwargs):
        events = self.get_events(year, month)
        calendar = MonthFullWeeksEventsCalendar(year, month, events)
        context = {
            "today": today,
            "calendar_type": self.calendar_type,
            "calendar": calendar
        }
        return context

    def get_events(self, year, month, **kwargs) -> Iterable:
        raise NotImplementedError()


class WeekEventsView(generic.TemplateView):
    def get(self, request, *args, **kwargs):
        """Validates GET-parameters, set defaults if no values provided."""
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        today_local = now_local(request.user.get_timezone()).date()
        today_iso_year, today_iso_week, _ = today_local.isocalendar()
        iso_year = query_params.validated_data.get('year', today_iso_year)
        iso_week = query_params.validated_data.get('week', today_iso_week)
        context = self.get_context_data(iso_year, iso_week, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, iso_year, iso_week, **kwargs):
        events = self.get_events(iso_year, iso_week)
        calendar = WeekEventsCalendar(iso_year, iso_week, events)
        context = {
            "calendar": calendar
        }
        return context

    def get_events(self, iso_year, iso_week,
                   **kwargs) -> Iterable[CalendarEvent]:
        raise NotImplementedError()
