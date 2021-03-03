from courses.calendar import CalendarEventFactory


def flatten_calendar_month_events(calendar_month):
    return [calendar_event for week in calendar_month.weeks
            for day in week.days
            for calendar_event in day.events]


def compare_calendar_events_with_models(calendar_events, objects):
    assert len(objects) == len(calendar_events)
    for obj in objects:
        assert CalendarEventFactory.create(obj, time_zone=None) in calendar_events
