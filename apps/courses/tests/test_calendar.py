import datetime

import pytest

from courses.calendar import (
    CalendarEventFactory, MonthFullWeeksEventsCalendar, WeekEventsCalendar
)
from courses.tests.factories import CourseClassFactory
# TODO: test CourseClassQuerySet manager
# TODO: test utils.get_boundaries
from courses.utils import MonthPeriod


@pytest.mark.django_db
def test_calendar_event():
    class_date = datetime.date(year=2018, month=2, day=3)
    course_class = CourseClassFactory(
        name='Event Name',
        date=class_date,
        starts_at=datetime.time(hour=11, minute=0),
        ends_at=datetime.time(hour=13, minute=0))
    calendar_event = CalendarEventFactory.create(course_class, time_zone=None)
    assert calendar_event.date == course_class.date
    assert calendar_event.starts_at == course_class.starts_at
    assert calendar_event.ends_at == course_class.ends_at
    assert calendar_event.name == course_class.course.meta_course.name
    assert calendar_event.description == course_class.name
    assert calendar_event.description == course_class.name


@pytest.mark.django_db
def test_month_events_calendar(client, settings):
    settings.LANGUAGE_CODE = 'ru'
    class_date = datetime.date(year=2018, month=2, day=3)
    course_classes = CourseClassFactory.create_batch(5, date=class_date)
    events = (CalendarEventFactory.create(e, time_zone=None) for e in course_classes)
    calendar = MonthFullWeeksEventsCalendar(month_period=MonthPeriod(2018, 2), events=events)
    assert calendar.next_month == datetime.date(year=2018, month=3, day=1)
    assert calendar.prev_month == datetime.date(year=2018, month=1, day=1)
    assert calendar.month_label == 'Февраль 2018'
    week_index = 0  # week index of the month
    events = calendar.weeks[week_index].days[class_date.weekday()].events
    assert len(events) == 5
    # Make sure events are sorted by `event.start_at`
    current_event = events[0]
    for e in events:
        assert e.starts_at <= current_event.starts_at
        current_event = e


@pytest.mark.django_db
def test_week_events_calendar(client, settings):
    settings.LANGUAGE_CODE = 'ru'
    class_date = datetime.date(year=2018, month=2, day=3)
    course_classes = CourseClassFactory.create_batch(5, date=class_date)
    next_week_start = datetime.date(year=2018, month=2, day=5)
    CourseClassFactory.create_batch(2, date=next_week_start)
    events = (CalendarEventFactory.create(e, time_zone=None) for e in course_classes)
    year, week_number, _ = class_date.isocalendar()
    calendar = WeekEventsCalendar(2018, week_number, events=events)
    assert calendar.week.monday() == datetime.date(year=2018, month=1, day=29)
    assert calendar.week.sunday() == datetime.date(year=2018, month=2, day=4)
    assert calendar.prev_week.week == 4
    assert calendar.week_label == "29 янв–04 фев 2018"
    assert len(calendar.days()) == 1
    events = calendar.days()[0].events
    assert len(events) == 5
    current_event = events[0]
    for e in events:
        assert e.starts_at <= current_event.starts_at
        current_event = e
