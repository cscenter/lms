from typing import Iterable, Union

from django.http import HttpResponseRedirect
from django.views import generic

from core.timezone import now_local, CityCode, Timezone
from courses.calendar import CalendarQueryParams, MonthEventsCalendar

__all__ = ('MonthEventsCalendarView',)


class MonthEventsCalendarView(generic.TemplateView):
    calendar_type = "full"
    template_name = "courses/calendar.html"

    def get(self, request, *args, **kwargs):
        """Validates GET-parameters, set defaults if no values provided."""
        query_params = CalendarQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        today = now_local(self.get_default_timezone()).date()
        year = query_params.validated_data.get('year', today.year)
        month = query_params.validated_data.get('month', today.month)
        context = self.get_context_data(year, month, today, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, year, month, today, **kwargs):
        events = self.get_events(year, month)
        calendar = MonthEventsCalendar(year, month, events)
        context = {
            "today": today,
            "calendar_type": self.calendar_type,
            "calendar": calendar
        }
        return context

    def get_events(self, year, month, **kwargs) -> Iterable:
        raise NotImplementedError()

    def get_default_timezone(self) -> Union[Timezone, CityCode]:
        """
        By default we redirect the authorized user to `current` month if
        no valid (or any) parameters were provided.

        This `current` value could depends on user locale settings.
        """
        raise NotImplementedError()
