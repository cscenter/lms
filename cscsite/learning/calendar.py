import datetime

from calendar import Calendar, monthrange
from collections import namedtuple, defaultdict
from django.utils import timezone
from itertools import chain

from learning.utils import grouper

__all__ = ['get_bounds_for_calendar_month', 'EventsCalendar']

MONDAY_WEEKDAY = 0
_CALENDAR = Calendar(firstweekday=MONDAY_WEEKDAY)
Week = namedtuple("Week", ['index', 'days'])
EventDay = namedtuple("EventDay", ['day', 'events', 'is_this_month', 'is_today'])


def get_bounds_for_calendar_month(year, month):
    """Returns calendar bounds of a month (inclusive)"""
    day1, days_in_month = monthrange(year, month)
    date = datetime.date(year, month, 1)
    # Go back to the beginning of the week
    days_before = (day1 - MONDAY_WEEKDAY) % 7
    days_after = (MONDAY_WEEKDAY - day1 - days_in_month) % 7
    start = date - datetime.timedelta(days=days_before)
    end = date + datetime.timedelta(days=days_in_month + days_after - 1)
    return start, end


class EventsCalendar:
    """
    This calendar can generate grid for month.
    Optionally you can attach events:
        calendar = EventsCalendar()
        calendar.add_events(*iterables)
        print(calendar.as_matrix(2017, 1))
    """
    MONDAY_WEEKDAY = 0

    def __init__(self):
        self.dates_to_events = defaultdict(list)

    @staticmethod
    def get_today(tz: datetime.tzinfo) -> datetime.datetime:
        return timezone.localtime(timezone.now(), timezone=tz)

    def add_events(self, *iterables):
        if len(iterables) > 1:
            _chain = chain(*iterables)
            events = sorted(_chain, key=lambda evt: (evt.date, evt.starts_at))
        else:
            events = iterables
        for event in events:
            self.dates_to_events[event.date].append(event)

    @staticmethod
    def get_bounds(year, month):
        return get_bounds_for_calendar_month(year, month)

    def as_matrix(self, year, month, today):
        """
        Return a matrix representing a month's calendar.
        Each row represents a week; week entries are tuple
        (week number, [EventDay])
        """
        by_week = []
        dates = _CALENDAR.itermonthdates(year, month)
        # FIXME: Is it useful? is_today and `is_this_month`?
        for week in grouper(dates, 7):
            week_number = week[0].isocalendar()[1]
            week_data = []
            for day in week:
                data = EventDay(day=day,
                                events=self.dates_to_events[day],
                                is_this_month=(day.month == month),
                                is_today=(today == day))
                week_data.append(data)
            by_week.append(Week(index=week_number, days=week_data))
        return by_week
