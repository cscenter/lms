from typing import Iterable

from django.http import HttpResponseRedirect
from django.views import generic

from core.timezone import now_local
from courses.calendar import CalendarQueryParams, MonthEventsCalendar

__all__ = ('MonthEventsCalendarView',)


class MonthEventsCalendarView(generic.TemplateView):
    calendar_type = "full"
    template_name = "learning/calendar.html"

    def get(self, request, *args, **kwargs):
        """Validates GET-parameters, set defaults if no values provided."""
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        city_code = self.get_user_city()
        today = now_local(city_code).date()
        year = query_params.validated_data.get('year', today.year)
        month = query_params.validated_data.get('month', today.month)
        context = self.get_context_data(year, month, city_code, today, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, year, month, default_city_code, today, **kwargs):
        events = self.get_events(year, month, user_city_code=default_city_code)
        calendar = MonthEventsCalendar(year, month, events)
        context = {
            "today": today,
            "calendar_type": self.calendar_type,
            "calendar": calendar
        }
        return context

    def get_events(self, year, month, **kwargs) -> Iterable:
        raise NotImplementedError()

    def get_user_city(self):
        """Returns city code for authenticated user"""
        raise NotImplementedError()
