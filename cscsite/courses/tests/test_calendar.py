import datetime

import pytest

from courses.calendar import MonthEventsCalendar, CalendarEvent
from courses.factories import CourseClassFactory, CourseFactory
from courses.models import CourseClass


def test_calendar_event():
    class_date = datetime.date(year=2018, month=2, day=3)
    course_class = CourseClass(
        course=CourseFactory.build(),
        name='Event Name',
        date=class_date,
        starts_at=datetime.time(hour=11, minute=0),
        ends_at=datetime.time(hour=13, minute=0))
    calendar_event = CalendarEvent(course_class)
    assert calendar_event.date == course_class.date
    assert calendar_event.start == '11:00'
    assert calendar_event.end == '13:00'
    assert calendar_event.name == course_class.course.meta_course.name
    assert calendar_event.description == course_class.name
    assert calendar_event.description == course_class.name


@pytest.mark.django_db
def test_month_events_calendar(client, settings):
    settings.LANGUAGE_CODE = 'ru'
    class_date = datetime.date(year=2018, month=2, day=3)
    course_classes = CourseClassFactory.create_batch(5, date=class_date)
    events = (CalendarEvent(e) for e in course_classes)
    calendar = MonthEventsCalendar(year=2018, month=2, events=events)
    assert calendar.next_month == datetime.date(year=2018, month=3,
                                                day=calendar._date.day)
    assert calendar.prev_month == datetime.date(year=2018, month=1,
                                                day=calendar._date.day)
    assert calendar.month_label == 'Февраль 2018'
    week_index = 0  # week index of the month
    events = calendar.weeks()[week_index].days[class_date.weekday()].events
    assert len(events) == 5
    # Make sure events are sorted by `event.start_at`
    current_event = events[0]
    for e in events:
        assert e.start <= current_event.start
        current_event = e
