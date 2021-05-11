from typing import Iterable

from rest_framework import serializers

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.views import generic

from api.utils import requires_context
from core.timezone import get_now_utc, now_local
from courses.calendar import (
    CalendarEvent, MonthFullWeeksEventsCalendar, WeekEventsCalendar
)

__all__ = ('MonthEventsCalendarView', 'WeekEventsView')

from courses.utils import MonthPeriod


def calendar_max_year(value):
    today = get_now_utc()
    if value > today.year + 1:
        raise ValidationError("Year value is too big")


@requires_context
def current_user_year(serializer_field):
    """Returns current year in the timezone of the current user"""
    return now_local(serializer_field.context['request'].user.time_zone).year


@requires_context
def current_user_month(serializer_field):
    """Returns current month in the timezone of the current user"""
    return now_local(serializer_field.context['request'].user.time_zone).month


class MonthEventsCalendarView(generic.TemplateView):
    calendar_type = "full"
    template_name = "lms/courses/calendar.html"

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField(required=False, default=current_user_year,
                                        min_value=settings.ESTABLISHED,
                                        validators=[calendar_max_year])
        month = serializers.IntegerField(required=False, default=current_user_month,
                                         min_value=1, max_value=12)

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.GET, context={'request': request})
        if not serializer.is_valid(raise_exception=False):
            return HttpResponseRedirect(request.path)
        month_period = MonthPeriod(year=serializer.validated_data['year'],
                                   month=serializer.validated_data['month'])
        events = self.get_events(month_period)
        calendar = MonthFullWeeksEventsCalendar(month_period, events)
        context = {
            "today": now_local(request.user.time_zone).date(),
            "calendar_type": self.calendar_type,
            "calendar": calendar
        }
        return self.render_to_response(context)

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable[CalendarEvent]:
        raise NotImplementedError()


@requires_context
def current_user_iso_week(serializer_field):
    """Returns current iso week in the timezone of the current user"""
    now_ = now_local(serializer_field.context['request'].user.time_zone)
    iso_year, iso_week, _ = now_.isocalendar()
    return iso_week


class WeekEventsView(generic.TemplateView):
    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField(required=False, default=current_user_year,
                                        min_value=settings.ESTABLISHED,
                                        validators=[calendar_max_year])
        # ISO week-numbering year has 52 or 53 full weeks
        week = serializers.IntegerField(required=False, default=current_user_iso_week,
                                        min_value=1, max_value=53)

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.GET, context={'request': request})
        if not serializer.is_valid(raise_exception=False):
            return HttpResponseRedirect(request.path)
        iso_year = serializer.validated_data['year']
        iso_week = serializer.validated_data['week']
        events = self.get_events(iso_year, iso_week)
        calendar = WeekEventsCalendar(iso_year, iso_week, events)
        context = {
            "calendar": calendar
        }
        return self.render_to_response(context)

    def get_events(self, iso_year, iso_week) -> Iterable[CalendarEvent]:
        raise NotImplementedError()
